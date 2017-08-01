#!/usr/bin/env python3

"""
This script parses the html files inside html/xssed/full and 
html/randomwalk/subsample as defined respectively in xssed.json and 
randomwalk.json. It outputs data.csv.
HTML files referenced on the json files that cannot be found will be discarted
(because the random sample was subsampled and some duplicated or very large
files were removed).

TODO:
- compile regex for performance
- change the structure of the code for easier reuse for prediction (?)
- verify that the HTML parser is resetted at the end of each file
- move to a better XML parser?
""" 

import json, csv, re, esprima
from urllib.parse import unquote as urldecode
from html.parser import HTMLParser

def import_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def write_csv(data, filename):
    with open(filename, 'w') as f:
        reader = csv.DictWriter(f, data[0].keys())
        reader.writeheader()
        reader.writerows(data)

class MyHTMLParser(HTMLParser):
    def __init__(self, 
            tags = ('script', 'iframe', 'meta', 'div'), # tags to count
            attrs = ('href', 'http-equiv', 'lowsrc'), # attributes to count
            eventHandlers = (), # eventHandlers to count. load it at call
        ):
        HTMLParser.__init__(self)
        self.data = {}
        self.tags = tags
        self.attrs = attrs
        self.eventHandlers = eventHandlers
        # HTML tags
        for tag in tags:
           self.data['html_tag_' + tag] = 0
        # HTML attrs
        for attr in attrs:
           self.data['html_attr_' + attr] = 0
        # Events Handlers
        for event in eventHandlers:
           self.data['html_event_' + event] = 0
        # reference to JS file
        self.data['js_file'] = False
        # Store JS strings for further processing
        self.javascript = [] # list of JS strings
        # JS will be extracted from <script> tag, event handlers, 
        # javascript: link, javascript: onsubmit
        # cf: https://stackoverflow.com/questions/12008172/how-many-ways-are-to-call-javascript-code-from-html

    def handle_starttag(self, tag, attrs):
        if tag in self.tags:
            self.data['html_tag_' + tag] += 1
        for attr in attrs:
            if attr[0] in self.attrs:
                self.data['html_attr_' + attr[0]] += 1
            if attr[0] in self.eventHandlers:
                self.data['html_event_' + attr[0]] += 1
                self.javascript.append(attr[1]) # javascript attached to the event
            js_protocol = re.search(r'^\s*javascript:(.*)', attr[1], 
                flags=(re.IGNORECASE|re.DOTALL))
                # ignore case, white space, and new line (important)
            if bool(js_protocol):
                code = js_protocol.group(1)
                # strip out "javascript:" to keep only the code
                self.javascript.append(code) # javascript protocol

        if tag == "script":
            self.inScript = True # we are in a script tag
            if 'src' in attrs:
                # don't check file extension. JS can be called from any file
                # extention
                self.data['js_file'] = True

    def handle_data(self, data):
        if self.inScript:
            self.javascript.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.inScript = False

def node_generator(node):
    """
    Generator that takes an Esprima object or a Esprima node and outputs child
    nodes.
    """
    # process
    yield node
    # contains other nodes
    for i in node: # key if node is a dict, element if node is a list
        if isinstance(i, list):
            for subnode in i:
                yield from node_generator(subnode)
        elif isinstance(i, dict):
            pass

    # if hasattr(node, 'body'):
    #     if isinstance(node.body, list):
    #         # list of nodes
    #     else:
    #         yield from node_generator(node.body)

def parse_javascript(string, 
        domObjects = ('windows', 'location', 'document'),
        properties = ('cookie', 'location', 'document'),
        methods = ('write', 'getElementsByTagName', 'alert', 'eval', 
            'fromCharCode')
    ):
    """ Parse a string representing JS code and return a dict containing 
    features"""
    data = {}
    data['js_length'] = len(string)
    # init 
    for i in domObjects:
        data['js_dom_'+i] = 0
    for i in properties:
        data['js_prop_'+i] = 0
    for i in domObjects:
        data['js_method_'+i] = 0
    data['js_define_function'] = 0
    data['js_string_max_length'] = None 
    stringsList = []
    functionsList = []
    # JS parser ported from JS to Python.
    # tolerant to continue if strict JS is not respected, see:
    # http://esprima.readthedocs.io/en/4.0/syntactic-analysis.html#tolerant-mode
    # for the definition of the tree, see:
    # https://github.com/estree/estree/blob/master/es5.md
    esprimaObject = esprima.parseScript(string, options={'tolerant':True, 
        'tokens': True}) #.toDict()
    parsedCode = esprimaObject.body
    for node in node_generator(parsedCode):
        if node.type in ['FunctionDeclaration', ]: # TODO: Function Declaration
            data['js_define_function'] += 1
        elif node.type in ['CallExpression',]: # Function or method scalls
            functionsList.append(node.callee.name)
    
    # number of functions used
    data['js_number_functions'] = len(set(functionsList)) # remove duplicates

    tokens = esprimaObject.tokens
    # TODO: switch to parseScript to detect dom, prop, and methods?
    # But be careful to this case:
    #    var test = alert;
    #    test();
    for token in tokens:
        if token.type == 'Identifier':
            if token.value in domObjects:
                data['js_dom_'+token.value] += 1
            elif token.value in properties:
                data['js_prop_'+token.value] += 1
            elif token.value in methods:
                data['js_method_'+token.value] += 1
        elif token.type == "string":
            stringsList.append(tokens.value)
    # max length of strings
    data['js_string_max_length'] = max([len(i) for i in stringsList])
    return data

def parse_html(filename):
    """ Parses filename and returns a dict of features for future model uses"""
    try:
        with open(filename, 'r') as f:
            html_data = f.read()
    except FileNotFoundError as e:
        #print("File not found. Skipping file: %s" % filename) # debug
        return None
    parser = MyHTMLParser()
    #data = {}
    parser.feed(html_data)
    #data = parser.data
    #javascript = parser.javascript
    #data['html_length'] = len(html_data)
    return data

def parse_url(string):
    """ Parses a URL as str and returns a dict of features for future model 
    uses"""
    string = urldecode(string)
    data = {}
    data['url_length'] = len(string)
    data['url_duplicated_characters'] = ('<<' in string) or ('>>' in string)
    data['url_special_characters'] = any(i in string for i in '"\'>')
        # ex: ", ">, "/> 
    data['url_script_tag'] = bool(re.search(r'<\s*script.*>|<\s*/\s*script\s*>',
        string, flags=re.IGNORECASE))
        # check for whitespace and ignore case
        # checked on https://www.owasp.org/index.php/XSS_Filter_Evasion_Cheat_Sheet
    data['url_cookie'] = ('document.cookie' in string)
    data['url_redirection'] = any(i in string for i in ['window.location', 
        'window.history', 'window.navigate', 'document.URL', 
        'document.documentURI', 'document.URLUnencoded', 'document.baseURI',
        'location', 'window.open', 'self.location', 'top.location'])
        # From paper:
        # window.location, window.history, window.navigate
        # From: https://code.google.com/archive/p/domxsswiki/wikis/LocationSources.wiki
        # document.URL, document.documentURI, document.URLUnencoded,
        # document.baseURI, location, location.href, location.search, 
        # location.hash, location.pathname
        # window.open
        # https://stackoverflow.com/a/21396837
        # self.location, top.location
        # jQuery: $(location).attr('href','http://www.example.com')
        #         $(window).attr('location','http://www.example.com')
        #         $(location).prop('href', 'http://www.example.com')
        # https://stackoverflow.com/a/4745012
        # document.location
    data['url_number_keywords'] = sum(i in string for i in ['login', 'signup', 
        'contact', 'search', 'query', 'redirect', # from "Prediction of 
        #Cross-Site Scriting Attack Using Machine Learning Algoritms"
        'XSS', 'banking', 'root', 'password', 'crypt', 'shell', 'evil' ])
        # from "Automatic Classification of Cross-Site Scripting in Web Pages Using Document-based and URL-based Features"
    data['url_number_domain'] = len(re.findall(
        r'(?:(?!-)[A-Za-z0-9-]{1,63}(?!-)\.)+[A-Za-z]{2,6}', string))
        # adapted from: http://www.mkyong.com/regular-expressions/domain-name-regular-expression-example/
        # idea to bypass: IDN domain names: https://stackoverflow.com/a/26987741
        # becareful to decode URL before 
    return data

def main():
    data = []
    data_rw = import_json('randomwalk.json')
    for page in data_rw:
        feature_class = {'class': 0} # benign
        # regexp to be compatible with spider before commit b651f88
        features_html = parse_html(re.sub(r'html/randomsample(/full)?/', 
            r'html/randomsample/subsample/', page['file_path']))
        if features_html is None: # file not found, do not write
            continue
        features_url = parse_url(page['url'])
        # merge dicts
        features_page = {**feature_class, **features_url, **features_html}
        data.append(features_page)
    data_xssed = import_json('xssed.json')
    for page in data_xssed:
        if page['category'] not in ['XSS', 'Script Insertion']:
            print('''Warning: non-XSS vuln imported. please check if it should
            be removed: %s''' % page['url'])
        feature_class = {'class': 1} # xss
        features_url = parse_url(page['url'])
        features_html = parse_html(page['files'][0]['path'])
        features_page = {**feature_class, **features_url, **features_html} # merge dicts
        data.append(features_page)
    write_csv(data, '../data.csv')

if __name__ == "__main__":
    main()
