#!/usr/bin/env python3
import hashlib
import http.client
import json
import sys
import urllib.parse

if len(sys.argv) != 5:
    raise SystemExit('usage: grp26xx-auth-read.py IP MODEL EXT PBX_IP')

ip, expected_model, expected_ext, pbx_ip = sys.argv[1:]
raw = sys.stdin.buffer.read(1024)
parts = raw.split(b'\0')
if len(parts) != 2 or not parts[0] or not parts[1]:
    raise SystemExit('credential input unavailable')
web_password = parts[0].decode('utf-8')
sip_secret = parts[1].decode('utf-8')
if len(web_password) > 128 or len(sip_secret) > 256:
    raise SystemExit('credential input invalid')

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': '*/*',
    'Host': ip,
    'Referer': 'http://%s/' % ip,
}
conn = http.client.HTTPConnection(ip, 80, timeout=6)
conn.request('GET', '/', headers=headers)
resp = conn.getresponse()
resp.read()
cookies = []
for name, value in resp.getheaders():
    if name.lower() == 'set-cookie':
        pair = value.split(';', 1)[0].strip()
        if pair:
            cookies.append(pair)
if cookies:
    headers['Cookie'] = '; '.join(cookies)

access = urllib.parse.urlencode({'access': hashlib.sha256(b'admin').hexdigest()})
conn.request('POST', '/cgi-bin/access', body=access, headers=headers)
resp = conn.getresponse()
reply = json.loads(resp.read().decode('utf-8', 'replace'))
nonce = reply.get('body', '')
if resp.status != 200 or reply.get('response') != 'success' or not isinstance(nonce, str) or not nonce:
    print('access_challenge=FAILED')
    raise SystemExit(1)
print('access_challenge=PASS')

digest = hashlib.sha256((web_password + nonce).encode('utf-8')).hexdigest()
body = urllib.parse.urlencode({'username': 'admin', 'password': digest})
conn.request('POST', '/cgi-bin/dologin', body=body, headers=headers)
resp = conn.getresponse()
reply = json.loads(resp.read().decode('utf-8', 'replace'))
payload = reply.get('body')
sid = payload.get('sid', '') if isinstance(payload, dict) else (payload if isinstance(payload, str) else '')
if resp.status != 200 or reply.get('response') != 'success' or not sid:
    print('login=FAILED')
    raise SystemExit(1)
print('login=PASS')
for name, value in resp.getheaders():
    if name.lower() == 'set-cookie':
        pair = value.split(';', 1)[0].strip()
        if pair and not pair.lower().startswith('session-identity='):
            cookies.append(pair)
cookies.append('session-identity=' + sid)
headers['Cookie'] = '; '.join(cookies)

pvalues = '1395,35,36,34,47,48,270,271,212,237,6767'
query = urllib.parse.urlencode({'pvalues': pvalues, 'sid': sid, 'update_session': 'true'})
conn.request('GET', '/cgi-bin/config_get?' + query, headers=headers)
resp = conn.getresponse()
data = json.loads(resp.read().decode('utf-8', 'replace'))
if resp.status != 200 or data.get('response') == 'error':
    print('config_read=FAILED')
    raise SystemExit(1)
raw_body = data.get('body', data.get('configs', {}))
if isinstance(raw_body, str):
    try:
        raw_body = json.loads(raw_body)
    except Exception:
        raw_body = {}
values = {}
if isinstance(raw_body, dict):
    values = {str(k): '' if v is None else str(v) for k, v in raw_body.items()}
elif isinstance(raw_body, list):
    for item in raw_body:
        if isinstance(item, dict):
            key = item.get('pvalue') or item.get('id') or item.get('name')
            if key is not None and 'value' in item:
                values[str(key)] = '' if item['value'] is None else str(item['value'])

def val(*names):
    for name in names:
        if name in values:
            return values[name].strip()
    return ''

model = val('phone_model', 'P1395', '1395').replace(' ', '').upper()
ext_id = val('P35', '35')
auth_id = val('P36', '36')
phone_secret = val('P34', '34')
sip_server = val('P47', '47')
enabled = val('P271', '271')

model_ok = model == expected_model.replace(' ', '').upper()
ext_ok = ext_id == expected_ext
auth_ok = auth_id == expected_ext
secret_ok = bool(phone_secret) and hashlib.sha256(phone_secret.encode()).digest() == hashlib.sha256(sip_secret.encode()).digest()
server_ok = sip_server in (pbx_ip, 'cei-pbx02.lamundial.hn') or pbx_ip in sip_server
account_enabled = enabled in ('1', 'true', 'TRUE')

print('config_read=PASS')
print('model_match=' + ('YES' if model_ok else 'NO'))
print('extension_match=' + ('YES' if ext_ok else 'NO'))
print('auth_id_match=' + ('YES' if auth_ok else 'NO'))
print('sip_secret_match=' + ('YES' if secret_ok else 'NO'))
print('sip_server_match=' + ('YES' if server_ok else 'NO'))
print('account1_enabled=' + ('YES' if account_enabled else 'NO'))
print('provisioning_server_present=' + ('YES' if val('P237', '237') else 'NO'))
print('firmware_upgrade_mode_present=' + ('YES' if val('P212', '212') else 'NO'))
print('phone_write=NO')

for ok in (model_ok, ext_ok, auth_ok, secret_ok, server_ok, account_enabled):
    if not ok:
        raise SystemExit(1)
print('GRP26XX-PROD-AUTH-READ-PASS')
