#!/usr/bin/env python3
"""Targeted read-only login probe to minimize the GXP1625 User-Agent requirement.

Only two unresolved variants are tested:
A) Accept */* with no explicit User-Agent.
B) Accept */* with a product-specific Issabel User-Agent.
Known prior evidence already covers the rejected baseline and accepted curl-like UA.
No response body, password, SID or cookie value is printed.
"""
import http.client
import json
import os
import time
from urllib.parse import urlencode

ip = os.environ.get('PHONE_IP', '192.168.1.167')
username = os.environ.get('PHONE_USERNAME', 'admin')
password = os.environ.get('PHONE_PASSWORD', '')
if not password:
    raise SystemExit('PHONE_PASSWORD missing')

payload = urlencode({'username': username, 'password': password})
base_headers = {
    'Accept': '*/*',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': ip,
    'Referer': 'http://%s/' % ip,
}

def probe(name, extra):
    flags = {
        'http_status_200': False,
        'content_type_json': False,
        'response_success': False,
        'body_dict': False,
        'sid_present': False,
    }
    try:
        headers = dict(base_headers)
        headers.update(extra)
        conn = http.client.HTTPConnection(ip, timeout=8)
        conn.request('POST', '/cgi-bin/dologin', body=payload, headers=headers)
        resp = conn.getresponse()
        flags['http_status_200'] = resp.status == 200
        flags['content_type_json'] = resp.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() == 'application/json'
        raw = resp.read().decode('utf-8', 'replace')
        try:
            obj = json.loads(raw)
        except Exception:
            obj = None
        flags['response_success'] = isinstance(obj, dict) and obj.get('response') == 'success'
        flags['body_dict'] = isinstance(obj, dict) and isinstance(obj.get('body'), dict)
        flags['sid_present'] = flags['body_dict'] and bool(obj['body'].get('sid'))
        conn.close()
    except Exception:
        pass
    accepted = all(flags.values())
    print('%s=%s|http200=%s|json=%s|success=%s|body=%s|sid=%s' % (
        name,
        'ACCEPTED' if accepted else 'REJECTED',
        'YES' if flags['http_status_200'] else 'NO',
        'YES' if flags['content_type_json'] else 'NO',
        'YES' if flags['response_success'] else 'NO',
        'YES' if flags['body_dict'] else 'NO',
        'YES' if flags['sid_present'] else 'NO',
    ))
    return accepted

print('scope=READ_ONLY_USER_AGENT_MINIMIZATION')
print('phone_write=NO')
print('db_write=NO')
print('secret_values_logged=NO')
print('variant_count=2')
accept_only = probe('accept_only_no_explicit_ua', {})
time.sleep(1)
generic = probe('accept_plus_issabel_ua', {'User-Agent': 'Issabel-EndpointConfig/5.0'})

if accept_only:
    decision = 'USER_AGENT_NOT_REQUIRED'
elif generic:
    decision = 'GENERIC_USER_AGENT_SUFFICIENT'
else:
    decision = 'KEEP_VALIDATED_CURL_LIKE_USER_AGENT'
print('decision=' + decision)
print('G10-19H8L-COMPLETE=YES')
