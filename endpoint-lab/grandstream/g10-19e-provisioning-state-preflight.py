#!/usr/bin/env python3
import http.client
import json
import os
import urllib.parse

PHONE_IP = os.environ.get('PHONE_IP', '192.168.1.167')
USERNAME = os.environ.get('PHONE_USERNAME', 'admin')
PASSWORD = os.environ.get('PHONE_PASSWORD', '')
PBX_IP = os.environ.get('PBX_IP', '192.168.1.10')
REPORT = os.environ.get('REPORT_PATH', 'g10-19e-provisioning-state-preflight.txt')

if not PASSWORD:
    raise SystemExit('PHONE_PASSWORD missing')

def log(line):
    print(line)
    with open(REPORT, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')

def request(conn, method, path, body, headers):
    conn.request(method, path, body=body, headers=headers)
    r = conn.getresponse()
    data = r.read().decode('utf-8', 'replace')
    return r.status, data

open(REPORT, 'w').close()
log('scope=READ_ONLY')
log('phone_write=NO')
log('target=GXP1625')

conn = http.client.HTTPConnection(PHONE_IP, 80, timeout=5)
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': PHONE_IP,
    'Referer': 'http://%s/' % PHONE_IP,
    'Accept': '*/*',
}
login_body = urllib.parse.urlencode({'username': USERNAME, 'password': PASSWORD})
status, raw = request(conn, 'POST', '/cgi-bin/dologin', login_body, headers)
try:
    login = json.loads(raw)
except Exception:
    login = {}
sid = login.get('body', {}).get('sid') or login.get('sid') or ''
accepted = status == 200 and login.get('response') == 'success' and bool(sid)
log('login=' + ('SUCCESS' if accepted else 'FAILED'))
log('login_http=' + str(status))
if not accepted:
    log('diagnostic=PHONE_LOGIN_FAILED')
    log('G10-19E-COMPLETE')
    raise SystemExit(0)

keys = 'P212:P237:P234:P235:P240:P1359:P1360:P1361:P6767'
read_body = urllib.parse.urlencode({'request': keys, 'sid': sid})
status, raw = request(conn, 'POST', '/cgi-bin/api.values.get', read_body, headers)
try:
    data = json.loads(raw)
except Exception:
    data = {}
body = data.get('body') if isinstance(data.get('body'), dict) else {}
read_ok = status == 200 and data.get('response') == 'success' and isinstance(body, dict)
log('read=' + ('SUCCESS' if read_ok else 'FAILED'))
log('read_http=' + str(status))
if not read_ok:
    log('diagnostic=PROVISIONING_STATE_READ_FAILED')
    log('G10-19E-COMPLETE')
    raise SystemExit(0)

def val(k):
    v = body.get(k)
    return '' if v is None else str(v)

def present(k):
    return k in body

for k in ('P212','P237','P234','P235','P240','P6767'):
    log(k.lower() + '_present=' + ('YES' if present(k) else 'NO'))

p212 = val('P212')
p237 = val('P237').strip()
log('p212_value=' + (p212 if p212 in ('0','1','2','3','4') else ('EMPTY' if p212 == '' else 'OTHER')))
if p237 == '':
    p237_target='EMPTY'
elif p237 == PBX_IP or p237.rstrip('/') == PBX_IP:
    p237_target='PBX_LAB'
elif PBX_IP in p237:
    p237_target='PBX_LAB_URL'
else:
    p237_target='OTHER'
log('p237_target=' + p237_target)
log('config_file_prefix_present=' + ('YES' if bool(val('P234')) else 'NO'))
log('config_file_postfix_present=' + ('YES' if bool(val('P235')) else 'NO'))
log('authenticate_config_value=' + (val('P240') if val('P240') in ('0','1') else ('EMPTY' if val('P240') == '' else 'OTHER')))
log('xml_config_password_present=' + ('YES' if bool(val('P1359')) else 'NO'))
log('config_http_username_present=' + ('YES' if bool(val('P1360')) else 'NO'))
log('config_http_password_present=' + ('YES' if bool(val('P1361')) else 'NO'))
log('firmware_upgrade_via=' + (val('P6767') if val('P6767') in ('0','1','2') else ('EMPTY' if val('P6767') == '' else 'OTHER')))

if p212 == '0' and p237_target in ('PBX_LAB','PBX_LAB_URL'):
    log('diagnostic=PHONE_ALREADY_POINTS_TO_PBX_TFTP')
    log('next_activity=G10-19F_PHONE_CFG_FETCH_PROOF')
else:
    log('diagnostic=PHONE_PROVISIONING_BOOTSTRAP_REQUIRED')
    log('next_activity=G10-19E2_CONTROLLED_BOOTSTRAP')
log('G10-19E-COMPLETE')
