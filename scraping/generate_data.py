#!/usr/bin/env python3

"""
This script parses the html files inside html/xssed/full and 
html/randomwalk/subsample as defined respectively in xssed.json and 
randomwalk.json. It outputs data.csv.
HTML files referenced on the json files that cannot be found will be discarted
(because some duplicated or very large files can be removed). 
""" 

import json, csv

def import_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def write_csv(data, filename):
    with open(filename, 'w') as f:
        reader = csv.DictWriter(f, data[0].keys())
        reader.writeheader()
        reader.writerows(data)

def parse_html(filename):
    """ Parses filename and returns a dict of features for future model uses"""
    try:
        with open(filename, 'r'):
            pass # TODO
    except FileNotFoundError as e:
        print("File not found. Skipping file: %s" % filename)
        return None
    data = {}
    data['html_length'] = len(string)
    return data

def parse_url(string):
    """ Parses a URL as str and returns a dict of features for future model 
    uses"""
    data = {}
    data['url_length'] = len(string)
    return data

def main():
    data = []
    data_rw = import_json('randomwalk.json')
    for page in data_rw:
        feature_class = {'class': 0} # benign
        features_html = parse_html(page['file_path'].replace(
            'html/randomsample/', 'html/randomsample/subsample/'))
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
