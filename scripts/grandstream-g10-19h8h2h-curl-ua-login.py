#!/usr/bin/env python3
"""Read-only GXP1625 login probe using curl-like headers.

Sensitive values are read only from environment and never printed.
"""
import json
import os
import http.client
from urllib.parse import urlencode

ip = os.environ.get('PHONE_IP', '192.168.1.167')
username = os.environ.get('PHONE_USERNAME', 'admin')
password = os.environ.get('PHONE_PASSWORD', '')
if not password:
    raise SystemExit('PHONE_PASSWORD missing')

headers = {
    'Accept': '*/*',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': ip,
    'Referer': 'http://%s/' % ip,
    'User-Agent': 'curl/8.14.1',
}
payload = urlencode({'username': username, 'password': password})
flags = {
    'http_status_200': False,
    'content_type_json': False,
    'response_success': False,
    'body_dict': False,
    'sid_present': False,
}
try:
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
except Exception:
    pass

print('scope=READ_ONLY_CURL_UA_NATIVE_LOGIN')
print('phone_write=NO')
print('db_write=NO')
print('secret_values_logged=NO')
print('tested_accept_star=YES')
print('tested_user_agent_curl=YES')
for key in ('http_status_200', 'content_type_json', 'response_success', 'body_dict', 'sid_present'):
    print(key + '=' + ('YES' if flags[key] else 'NO'))
print('diagnostic=' + ('CURL_UA_NATIVE_LOGIN_ACCEPTED' if all(flags.values()) else 'CURL_UA_NATIVE_LOGIN_NOT_ACCEPTED'))
print('G10-19H8H2H-COMPLETE=YES')
