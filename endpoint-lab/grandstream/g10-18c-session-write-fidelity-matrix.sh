#!/usr/bin/env bash
set -euo pipefail

PHONE_IP="${PHONE_IP:-192.168.1.167}"
TUNNEL_HOST="${TUNNEL_HOST:-phone1.nocpbx.com}"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"
REPORT="${1:-g10-18c-session-write-fidelity-matrix.txt}"

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
json_field() { jq -r "$2 // empty" "$1" 2>/dev/null || true; }

make_login_form() {
  local out="$1"
  python3 - "$USERNAME" "$PASSWORD" "$out" <<'PY'
import sys, urllib.parse
user, password, out = sys.argv[1], sys.argv[2], sys.argv[3]
body = urllib.parse.urlencode({'username': user, 'password': password})
with open(out, 'wb') as fh:
    fh.write(body.encode('ascii'))
PY
  chmod 600 "$out"
}

make_read_form() {
  local out="$1" sid="$2"
  python3 - "$sid" "$out" <<'PY'
import sys, urllib.parse
sid, out = sys.argv[1], sys.argv[2]
body = urllib.parse.urlencode({'request': 'P208', 'sid': sid})
with open(out, 'wb') as fh:
    fh.write(body.encode('ascii'))
PY
  chmod 600 "$out"
}

make_write_form() {
  local out="$1" p208="$2" sid="$3"
  python3 - "$p208" "$sid" "$out" <<'PY'
import sys, urllib.parse
p208, sid, out = sys.argv[1], sys.argv[2], sys.argv[3]
body = urllib.parse.urlencode({'P208': p208, 'sid': sid})
with open(out, 'wb') as fh:
    fh.write(body.encode('ascii'))
PY
  chmod 600 "$out"
}

run_case() {
  local name="$1" base="$2" proto="$3" mode="$4" use_cookie="$5"
  local login_form="$TMP/$name.login.form" login_body="$TMP/$name.login.body" login_hdr="$TMP/$name.login.hdr"
  local read_form="$TMP/$name.read.form" read_body="$TMP/$name.read.body" read_hdr="$TMP/$name.read.hdr"
  local write_form="$TMP/$name.write.form" write_body="$TMP/$name.write.body" write_hdr="$TMP/$name.write.hdr"
  local cookie="$TMP/$name.cookie"
  : > "$cookie"; chmod 600 "$cookie"
  make_login_form "$login_form"

  local common=( -sS "$proto" --connect-timeout 5 --max-time 20 -H 'Accept: */*' -H 'Content-Type: application/x-www-form-urlencoded' )
  case "$mode" in
    host_referer)
      common+=( -H "Referer: $base/" )
      ;;
    browser)
      common+=( -H "Origin: $base" -H "Referer: $base/" -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36' )
      ;;
  esac

  local cookie_login=() cookie_next=()
  if [ "$use_cookie" = YES ]; then
    cookie_login=( -c "$cookie" )
    cookie_next=( -b "$cookie" -c "$cookie" )
  fi

  local meta rc
  set +e
  meta=$(curl "${common[@]}" "${cookie_login[@]}" -D "$login_hdr" -o "$login_body" -w '%{http_code}|%{http_version}' --data-binary @"$login_form" "$base/cgi-bin/dologin" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=LOGIN_TRANSPORT_FAILED|curl_rc=$rc|cookie=$use_cookie"
    return
  fi

  local login_http="${meta%%|*}" login_ver="${meta#*|}" login_resp sid
  login_resp=$(json_field "$login_body" '.response')
  sid=$(json_field "$login_body" '.body.sid')
  if [ "$login_http" != 200 ] || [ "$login_resp" != success ] || [ -z "$sid" ]; then
    log "$name=LOGIN_FAILED|http=$login_http|http_version=$login_ver|response=${login_resp:-EMPTY}|sid_present=$( [ -n "$sid" ] && echo YES || echo NO )|cookie=$use_cookie"
    return
  fi

  make_read_form "$read_form" "$sid"
  set +e
  meta=$(curl "${common[@]}" "${cookie_next[@]}" -D "$read_hdr" -o "$read_body" -w '%{http_code}|%{http_version}' --data-binary @"$read_form" "$base/cgi-bin/api.values.get" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=READ_TRANSPORT_FAILED|curl_rc=$rc|login_http_version=$login_ver|cookie=$use_cookie"
    return
  fi

  local read_http="${meta%%|*}" read_ver="${meta#*|}" read_resp p208
  read_resp=$(json_field "$read_body" '.response')
  p208=$(json_field "$read_body" '.body.P208')
  if [ "$read_http" != 200 ] || [ "$read_resp" != success ] || [ -z "$p208" ]; then
    log "$name=READ_FAILED|login_http_version=$login_ver|read_http=$read_http|read_http_version=$read_ver|read_response=${read_resp:-EMPTY}|p208_present=$( [ -n "$p208" ] && echo YES || echo NO )|cookie=$use_cookie"
    return
  fi

  make_write_form "$write_form" "$p208" "$sid"
  set +e
  meta=$(curl "${common[@]}" "${cookie_next[@]}" -D "$write_hdr" -o "$write_body" -w '%{http_code}|%{http_version}' --data-binary @"$write_form" "$base/cgi-bin/api.values.post" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=WRITE_TRANSPORT_FAILED|curl_rc=$rc|read_http_version=$read_ver|cookie=$use_cookie"
    return
  fi

  local post_http="${meta%%|*}" post_ver="${meta#*|}" post_resp post_status result
  post_resp=$(json_field "$write_body" '.response')
  post_status=$(json_field "$write_body" '.body.status')
  result=WRITE_REJECTED_OTHER
  if [ "$post_http" = 200 ] && [ "$post_resp" = success ]; then result=WRITE_ACCEPTED; fi
  if [ "$post_status" = session-expired ]; then result=WRITE_SESSION_EXPIRED; fi

  log "$name=$result|login_http_version=$login_ver|read_http_version=$read_ver|post_http=$post_http|post_http_version=$post_ver|post_response=${post_resp:-EMPTY}|post_status=${post_status:-EMPTY}|cookie=$use_cookie"
}

log '=== G10-18C GRANDSTREAM SESSION / WRITE FIDELITY MATRIX ==='
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=SAME-VALUE-P208-ONLY_AFTER_SUCCESSFUL_READ'
log 'credential_values_logged=NO'
log 'session_values_logged=NO'
log 'basis=G10-18B_ACCEPTED_LOGIN_PROFILES_ONLY'

run_case lan_host_referer_nocookie "http://$PHONE_IP" --http1.1 host_referer NO
run_case lan_host_referer_cookie "http://$PHONE_IP" --http1.1 host_referer YES
run_case lan_browser_nocookie "http://$PHONE_IP" --http1.1 browser NO
run_case lan_browser_cookie "http://$PHONE_IP" --http1.1 browser YES
run_case tunnel_http11_nocookie "https://$TUNNEL_HOST" --http1.1 browser NO
run_case tunnel_http11_cookie "https://$TUNNEL_HOST" --http1.1 browser YES
run_case tunnel_http2_nocookie "https://$TUNNEL_HOST" --http2 browser NO
run_case tunnel_http2_cookie "https://$TUNNEL_HOST" --http2 browser YES
run_case tunnel_http3_nocookie "https://$TUNNEL_HOST" --http3 browser NO
run_case tunnel_http3_cookie "https://$TUNNEL_HOST" --http3 browser YES

log 'G10-18C-COMPLETE'
