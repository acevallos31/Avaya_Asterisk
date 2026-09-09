#!/usr/bin/env bash
set -euo pipefail

PHONE_IP="${PHONE_IP:-192.168.1.167}"
TUNNEL_HOST="${TUNNEL_HOST:-phone1.nocpbx.com}"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"
REPORT="${1:-g10-18d-read-shape-diagnostic.txt}"

if [ -z "$PASSWORD" ]; then
  echo "ERROR: GRANDSTREAM_HTTP_PASSWORD missing" >&2
  exit 2
fi

TMP="$(mktemp -d)"
chmod 700 "$TMP"
trap 'rm -rf "$TMP"' EXIT
: > "$REPORT"
chmod 600 "$REPORT"

log() { printf '%s\n' "$1" | tee -a "$REPORT"; }

make_form() {
  local out="$1" kind="$2" sid="${3:-}" req="${4:-}"
  python3 - "$USERNAME" "$PASSWORD" "$out" "$kind" "$sid" "$req" <<'PY'
import sys, urllib.parse
user,password,out,kind,sid,req=sys.argv[1:]
if kind=='login': data={'username':user,'password':password}
else: data={'request':req,'sid':sid}
with open(out,'wb') as f: f.write(urllib.parse.urlencode(data).encode('ascii'))
PY
  chmod 600 "$out"
}

shape_report() {
  python3 - "$1" <<'PY'
import json,sys
p=sys.argv[1]
try:
    j=json.load(open(p,encoding='utf-8'))
except Exception:
    print('json_valid=NO|response=EMPTY|body_type=NONE|body_keys=NONE|p208_anywhere=NO|p35_anywhere=NO')
    raise SystemExit

def typ(v):
    if isinstance(v,dict): return 'object'
    if isinstance(v,list): return 'array'
    if isinstance(v,str): return 'string'
    if isinstance(v,bool): return 'boolean'
    if v is None: return 'null'
    if isinstance(v,(int,float)): return 'number'
    return type(v).__name__

def find_key(v,key):
    if isinstance(v,dict):
        if key in v: return True
        return any(find_key(x,key) for x in v.values())
    if isinstance(v,list): return any(find_key(x,key) for x in v)
    return False
body=j.get('body')
keys=','.join(sorted(str(k) for k in body.keys())) if isinstance(body,dict) else 'NONE'
print('json_valid=YES|response=%s|body_type=%s|body_keys=%s|p208_anywhere=%s|p35_anywhere=%s' % (
    str(j.get('response','EMPTY')), typ(body), keys or 'NONE',
    'YES' if find_key(j,'P208') else 'NO', 'YES' if find_key(j,'P35') else 'NO'))
PY
}

run_case() {
  local name="$1" base="$2" proto="$3" request_value="$4" use_cookie="$5"
  local lf="$TMP/$name.login.form" lb="$TMP/$name.login.body" lh="$TMP/$name.login.hdr"
  local rf="$TMP/$name.read.form" rb="$TMP/$name.read.body" rh="$TMP/$name.read.hdr" cj="$TMP/$name.cookie"
  : > "$cj"; chmod 600 "$cj"
  make_form "$lf" login
  local common=( -sS "$proto" --connect-timeout 5 --max-time 20 -H 'Accept: */*' -H 'Content-Type: application/x-www-form-urlencoded' -H "Origin: $base" -H "Referer: $base/" -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36' )
  local c_login=() c_next=()
  if [ "$use_cookie" = YES ]; then c_login=( -c "$cj" ); c_next=( -b "$cj" -c "$cj" ); fi
  local meta rc
  set +e
  meta=$(curl "${common[@]}" "${c_login[@]}" -D "$lh" -o "$lb" -w '%{http_code}|%{http_version}' --data-binary @"$lf" "$base/cgi-bin/dologin" 2>/dev/null); rc=$?
  set -e
  if [ $rc -ne 0 ]; then log "$name=LOGIN_TRANSPORT_FAILED|curl_rc=$rc|cookie=$use_cookie"; return; fi
  local login_http="${meta%%|*}" login_ver="${meta#*|}" sid login_resp
  login_resp=$(jq -r '.response // empty' "$lb" 2>/dev/null || true)
  sid=$(jq -r '.body.sid // empty' "$lb" 2>/dev/null || true)
  if [ "$login_http" != 200 ] || [ "$login_resp" != success ] || [ -z "$sid" ]; then log "$name=LOGIN_FAILED|http=$login_http|http_version=$login_ver|cookie=$use_cookie"; return; fi
  make_form "$rf" read "$sid" "$request_value"
  set +e
  meta=$(curl "${common[@]}" "${c_next[@]}" -D "$rh" -o "$rb" -w '%{http_code}|%{http_version}' --data-binary @"$rf" "$base/cgi-bin/api.values.get" 2>/dev/null); rc=$?
  set -e
  if [ $rc -ne 0 ]; then log "$name=READ_TRANSPORT_FAILED|curl_rc=$rc|login_http_version=$login_ver|cookie=$use_cookie|request=$request_value"; return; fi
  local read_http="${meta%%|*}" read_ver="${meta#*|}" shape cookie_count
  shape=$(shape_report "$rb")
  cookie_count=$(grep -ci '^Set-Cookie:' "$lh" 2>/dev/null || true)
  log "$name=READ_SHAPE|login_http_version=$login_ver|read_http=$read_http|read_http_version=$read_ver|cookie=$use_cookie|login_set_cookie_count=$cookie_count|request=$request_value|$shape"
}

log '=== G10-18D GRANDSTREAM READ SHAPE DIAGNOSTIC ==='
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=NO'
log 'credential_values_logged=NO'
log 'session_values_logged=NO'
log 'response_values_logged=NO'
log 'purpose=RESOLVE_API_VALUES_GET_RESPONSE_SHAPE'

for req in P208 P35:P208 P208:P35; do
  run_case "lan_${req//:/_}_nocookie" "http://$PHONE_IP" --http1.1 "$req" NO
  run_case "lan_${req//:/_}_cookie" "http://$PHONE_IP" --http1.1 "$req" YES
  run_case "tunnel_h2_${req//:/_}_nocookie" "https://$TUNNEL_HOST" --http2 "$req" NO
  run_case "tunnel_h2_${req//:/_}_cookie" "https://$TUNNEL_HOST" --http2 "$req" YES
done

log 'G10-18D-COMPLETE'
