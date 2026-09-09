#!/usr/bin/env bash
set -euo pipefail

PHONE_IP="${PHONE_IP:-192.168.1.167}"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"
REPORT="${1:-g10-18g-forum-session-cookie-write-proof.txt}"

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
user, password, out = sys.argv[1:4]
with open(out, 'wb') as fh:
    fh.write(urllib.parse.urlencode({'username': user, 'password': password}).encode('ascii'))
PY
  chmod 600 "$out"
}

make_read_form() {
  local out="$1" sid="$2"
  python3 - "$sid" "$out" <<'PY'
import sys, urllib.parse
sid, out = sys.argv[1:3]
with open(out, 'wb') as fh:
    fh.write(urllib.parse.urlencode({'request': 'P35:P208', 'sid': sid}).encode('ascii'))
PY
  chmod 600 "$out"
}

make_write_form() {
  local out="$1" p208="$2" sid="$3"
  python3 - "$p208" "$sid" "$out" <<'PY'
import sys, urllib.parse
p208, sid, out = sys.argv[1:4]
with open(out, 'wb') as fh:
    fh.write(urllib.parse.urlencode({'P208': p208, 'sid': sid}).encode('ascii'))
PY
  chmod 600 "$out"
}

login_once() {
  local prefix="$1"
  local login_form="$TMP/$prefix.login.form" login_body="$TMP/$prefix.login.body" login_hdr="$TMP/$prefix.login.hdr"
  make_login_form "$login_form"
  local meta rc
  set +e
  meta=$(curl -sS --http1.1 --connect-timeout 5 --max-time 20 \
    -H 'Accept: */*' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H "Origin: http://$PHONE_IP" \
    -H "Referer: http://$PHONE_IP/" \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36' \
    -D "$login_hdr" -o "$login_body" -w '%{http_code}|%{http_version}' \
    --data-binary @"$login_form" "http://$PHONE_IP/cgi-bin/dologin" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    printf 'TRANSPORT_FAILED||%s\n' "$rc"
    return
  fi
  local http="${meta%%|*}" ver="${meta#*|}" resp sid
  resp=$(json_field "$login_body" '.response')
  sid=$(json_field "$login_body" '.body.sid')
  if [ "$http" != 200 ] || [ "$resp" != success ] || [ -z "$sid" ]; then
    printf 'LOGIN_FAILED|%s|%s\n' "$http" "$ver"
    return
  fi
  printf 'SUCCESS|%s|%s|%s\n' "$http" "$ver" "$sid"
}

run_case() {
  local name="$1" mode="$2"
  local login_result state login_http login_ver sid
  login_result=$(login_once "$name")
  IFS='|' read -r state login_http login_ver sid <<< "$login_result"
  if [ "$state" != SUCCESS ]; then
    log "$name=$state|login_http=${login_http:-NA}|login_http_version=${login_ver:-NA}"
    return
  fi

  local read_form="$TMP/$name.read.form" read_body="$TMP/$name.read.body" read_hdr="$TMP/$name.read.hdr"
  make_read_form "$read_form" "$sid"

  local meta rc
  set +e
  meta=$(curl -sS --http1.1 --connect-timeout 5 --max-time 20 \
    -H 'Accept: */*' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H "Origin: http://$PHONE_IP" \
    -H "Referer: http://$PHONE_IP/" \
    -H "Cookie: session_id=$sid" \
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36' \
    -D "$read_hdr" -o "$read_body" -w '%{http_code}|%{http_version}' \
    --data-binary @"$read_form" "http://$PHONE_IP/cgi-bin/api.values.get" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=READ_TRANSPORT_FAILED|curl_rc=$rc|explicit_session_id_cookie=YES"
    return
  fi

  local read_http="${meta%%|*}" read_ver="${meta#*|}" read_resp key_present p208_type p208
  read_resp=$(json_field "$read_body" '.response')
  key_present=$(jq -r 'if (.body|type)=="object" and (.body|has("P208")) then "YES" else "NO" end' "$read_body" 2>/dev/null || echo NO)
  p208_type=$(jq -r 'if (.body|type)=="object" and (.body|has("P208")) then (.body.P208|type) else "missing" end' "$read_body" 2>/dev/null || echo invalid)
  if [ "$read_http" != 200 ] || [ "$read_resp" != success ] || [ "$key_present" != YES ] || [ "$p208_type" = null ]; then
    log "$name=READ_FAILED|read_http=$read_http|read_http_version=$read_ver|read_response=${read_resp:-EMPTY}|p208_key_present=$key_present|p208_type=$p208_type|explicit_session_id_cookie=YES"
    return
  fi
  p208=$(jq -r '.body.P208' "$read_body")

  local write_body="$TMP/$name.write.body" write_hdr="$TMP/$name.write.hdr" write_form="$TMP/$name.write.form"
  local write_args=( -sS --http1.1 --connect-timeout 5 --max-time 20
    -H 'Accept: */*'
    -H "Origin: http://$PHONE_IP"
    -H "Referer: http://$PHONE_IP/"
    -H "Cookie: session_id=$sid"
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36'
    -D "$write_hdr" -o "$write_body" -w '%{http_code}|%{http_version}' )

  if [ "$mode" = urlencoded ]; then
    make_write_form "$write_form" "$p208" "$sid"
    write_args+=( -H 'Content-Type: application/x-www-form-urlencoded' --data-binary @"$write_form" )
  elif [ "$mode" = multipart ]; then
    write_args+=( -F "P208=$p208" -F "sid=$sid" )
  else
    log "$name=INTERNAL_MODE_ERROR"
    return
  fi

  set +e
  meta=$(curl "${write_args[@]}" "http://$PHONE_IP/cgi-bin/api.values.post" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=WRITE_TRANSPORT_FAILED|curl_rc=$rc|mode=$mode|explicit_session_id_cookie=YES"
    return
  fi

  local post_http="${meta%%|*}" post_ver="${meta#*|}" post_resp post_status diagnostic
  post_resp=$(json_field "$write_body" '.response')
  post_status=$(json_field "$write_body" '.body.status')
  diagnostic=WRITE_REJECTED_OTHER
  if [ "$post_http" = 200 ] && [ "$post_resp" = success ]; then diagnostic=WRITE_ACCEPTED; fi
  if [ "$post_status" = session-expired ]; then diagnostic=WRITE_SESSION_EXPIRED; fi

  log "$name=$diagnostic|login=SUCCESS|read=SUCCESS|p208_key_present=YES|p208_type=$p208_type|mode=$mode|explicit_session_id_cookie=YES|post_http=$post_http|post_http_version=$post_ver|post_response=${post_resp:-EMPTY}|post_status=${post_status:-EMPTY}"
}

log '=== G10-18G GRANDSTREAM FORUM-GUIDED SESSION COOKIE WRITE PROOF ==='
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=SAME-VALUE-P208-ONLY_AFTER_SUCCESSFUL_READ'
log 'credential_values_logged=NO'
log 'session_values_logged=NO'
log 'p208_value_logged=NO'
log 'basis=COMMUNITY_GRANDSTREAM_SCRIPTS_USE_EXPLICIT_session_id_COOKIE_AND_SID_FORM_FIELD'

run_case lan_explicit_session_cookie_urlencoded urlencoded
run_case lan_explicit_session_cookie_multipart multipart

log 'G10-18G-COMPLETE'
