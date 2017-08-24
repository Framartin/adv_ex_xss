import sys
import json
sys.path.append('..')
from scraping import generate_data as parser


def main():
    """
    Import payloads.json and returns a dict of features corresponding
    to the features modified by an attack using these payloads.
    Ex: using the payload "<script>alert(0)</script>" will add 1 to 
    'html_tag_script' and 'js_method_alert', and can possibly modify
    'js_min_length'.
    """
    data = []
    payload_reflected = {'xss_type': 'reflected'}
    payload_stored = {'xss_type': 'stored'}
    payloads = parser.import_json('payloads.json')
    for payload in payloads:
        # keep track of which payloads and remove other items
        payload_info = {key: payload[key] for key in payload.keys() if key in ['xss_injection', 'xss_string']}
        # we suppose that the attackers found a vulnerable URL parameter
        data_url = parser.parse_url('&param='+payload['xss_string'])
        if payload['xss_injection'] == 'tag':
            # in case of tag injection, the attacker found a way to add the payload
            data_html = parser.parse_html(payload['xss_string'])
        # below, we suppose that we are exploting a Source XSS. Client XSS (~ DOM-based XSS)
        # are out of scope
        # attack data if payload used in a reflected XSS
        data_attack = {**payload_info, **payload_reflected, **data_url, **data_html}
        data.append(data_attack)
        # attack data if payload used in a stored XSS
        data_attack = {**payload_info, **payload_stored, **data_html}
        data.append(data_attack)
    parser.write_csv(data, 'attacks.csv')

if __name__ == "__main__":
    main()
