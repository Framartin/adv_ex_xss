#!/usr/bin/env python3

"""
This script parses the html files inside html/xssed/full and 
html/randomwalk/subsample as defined respectively in xssed.json and 
randomwalk.json. It outputs data.csv.
HTML files referenced on the json files that cannot be found will be discarted
(because the random sample was subsampled and some duplicated or very large
files were removed).
""" 

import json, csv, re
from urllib.parse import unquote as urldecode
from HTMLParser import HTMLParser

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
            eventHandlers = () # eventHandlers to count. load it at call
        ):
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

    def handle_data(self, data):
        print "Encountered some data  :", data

def parse_html(filename):
    """ Parses filename and returns a dict of features for future model uses"""
    try:
        with open(filename, 'r'):
            pass # TODO
    except FileNotFoundError as e:
        #print("File not found. Skipping file: %s" % filename) # debug
        return None
    parser = MyHTMLParser()
    parser.feed()#TODO
    data = {}
    data['html_length'] = len(string)
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
