#!/usr/bin/env python3
"""Prepare a restricted read-only native login proof using the known-good secret.

The candidate password is accepted on stdin by the privileged helper, moved only
into a short-lived child environment, and never printed or passed in argv.
"""
from pathlib import Path
p=Path('deploy/j129/avaya-j129-lab-deploy')
s=p.read_text(encoding='utf-8')
marker='# G10-19H8H2G-KNOWN-GOOD-NATIVE-LOGIN'
if marker in s:
    print('G10-19H8H2G-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)
anchor='\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor)!=1: raise SystemExit('H8H2G action anchor missing')
func=r'''

# G10-19H8H2G-KNOWN-GOOD-NATIVE-LOGIN
prove_grandstream_known_good_native_login() {
  local supplied
  IFS= read -r supplied
  [ -n "$supplied" ] || { echo 'ERROR: known-good password missing on stdin' >&2; exit 1; }
  GS_H8H2G_PASSWORD="$supplied" python3 - <<'PY'
import os, json, http.client
from urllib.parse import urlencode
ip='192.168.1.167'
password=os.environ.get('GS_H8H2G_PASSWORD','')
headers={
    'Content-Type':'application/x-www-form-urlencoded',
    'Host':ip,
    'Referer':'http://%s/' % ip,
}
payload=urlencode({'username':'admin','password':password})
response_success=False; body_dict=False; sid_present=False; http_status='NONE'; ctype_json=False
try:
    conn=http.client.HTTPConnection(ip, timeout=8)
    conn.request('POST','/cgi-bin/dologin',body=payload,headers=headers)
    resp=conn.getresponse(); http_status=str(resp.status)
    ctype=(resp.headers.get('Content-Type','').split(';',1)[0].strip().lower())
    ctype_json=(ctype=='application/json')
    raw=resp.read().decode('utf-8','replace')
    try: obj=json.loads(raw)
    except Exception: obj=None
    response_success=isinstance(obj,dict) and obj.get('response')=='success'
    body_dict=isinstance(obj,dict) and isinstance(obj.get('body'),dict)
    sid_present=body_dict and bool(obj['body'].get('sid'))
except Exception:
    pass
print('scope=READ_ONLY_KNOWN_GOOD_NATIVE_LOGIN')
print('phone_write=NO')
print('db_write=NO')
print('secret_values_logged=NO')
print('http_status_200='+('YES' if http_status=='200' else 'NO'))
print('content_type_json='+('YES' if ctype_json else 'NO'))
print('response_success='+('YES' if response_success else 'NO'))
print('body_dict='+('YES' if body_dict else 'NO'))
print('sid_present='+('YES' if sid_present else 'NO'))
if http_status=='200' and ctype_json and response_success and body_dict and sid_present:
    print('diagnostic=KNOWN_GOOD_SECRET_NATIVE_LOGIN_ACCEPTED')
else:
    print('diagnostic=KNOWN_GOOD_SECRET_NATIVE_LOGIN_NOT_ACCEPTED')
print('G10-19H8H2G-COMPLETE=YES')
PY
  supplied=''
}
'''
s=s.replace(anchor,func+anchor,1)
case_anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s: raise SystemExit('H8H2G case anchor missing')
s=s.replace(case_anchor,case_anchor+'\n  prove-grandstream-known-good-native-login) [ -z "$OVERLAY_ROOT" ] || usage; prove_grandstream_known_good_native_login ;;',1)
p.write_text(s,encoding='utf-8')
print('G10-19H8H2G-HELPER-PREPARE=PASS')
