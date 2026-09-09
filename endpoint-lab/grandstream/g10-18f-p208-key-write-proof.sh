#!/usr/bin/env bash
set -euo pipefail

PHONE_IP="${PHONE_IP:-192.168.1.167}"
TUNNEL_HOST="${TUNNEL_HOST:-phone1.nocpbx.com}"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"
REPORT="${1:-g10-18f-p208-key-write-proof.txt}"

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

make_form() {
  local kind="$1" out="$2" a="${3:-}" b="${4:-}"
  python3 - "$kind" "$out" "$a" "$b" <<'PY'
import sys, urllib.parse
kind, out, a, b = sys.argv[1:5]
if kind == 'login':
    data = {'username': a, 'password': b}
elif kind == 'read':
    data = {'request': 'P208', 'sid': a}
elif kind == 'write':
    data = {'P208': a, 'sid': b}
else:
    raise SystemExit(2)
with open(out, 'wb') as fh:
    fh.write(urllib.parse.urlencode(data).encode('ascii'))
PY
  chmod 600 "$out"
}

run_case() {
  local name="$1" base="$2" proto="$3"
  local login_form="$TMP/$name.login.form" login_body="$TMP/$name.login.body" login_hdr="$TMP/$name.login.hdr"
  local read_form="$TMP/$name.read.form" read_body="$TMP/$name.read.body" read_hdr="$TMP/$name.read.hdr"
  local write_form="$TMP/$name.write.form" write_body="$TMP/$name.write.body" write_hdr="$TMP/$name.write.hdr"
  local cookie="$TMP/$name.cookie"
  : > "$cookie"; chmod 600 "$cookie"
  make_form login "$login_form" "$USERNAME" "$PASSWORD"

  local common=( -sS "$proto" --connect-timeout 5 --max-time 20
    -H 'Accept: */*'
    -H 'Content-Type: application/x-www-form-urlencoded'
    -H "Origin: $base"
    -H "Referer: $base/"
    -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36' )

  local meta rc
  set +e
  meta=$(curl "${common[@]}" -D "$login_hdr" -c "$cookie" -o "$login_body" -w '%{http_code}|%{http_version}' --data-binary @"$login_form" "$base/cgi-bin/dologin" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then log "$name=LOGIN_TRANSPORT_FAILED|curl_rc=$rc"; return; fi

  local login_http="${meta%%|*}" login_ver="${meta#*|}" login_resp sid cookie_count
  login_resp=$(json_field "$login_body" '.response')
  sid=$(json_field "$login_body" '.body.sid')
  cookie_count=$(awk 'BEGIN{IGNORECASE=1;c=0} /^Set-Cookie:/{c++} END{print c}' "$login_hdr")
  if [ "$login_http" != 200 ] || [ "$login_resp" != success ] || [ -z "$sid" ]; then
    log "$name=LOGIN_FAILED|http=$login_http|http_version=$login_ver|response=${login_resp:-EMPTY}|sid_present=$( [ -n "$sid" ] && echo YES || echo NO )|set_cookie_count=$cookie_count"
    return
  fi

  make_form read "$read_form" "$sid"
  set +e
  meta=$(curl "${common[@]}" -D "$read_hdr" -b "$cookie" -c "$cookie" -o "$read_body" -w '%{http_code}|%{http_version}' --data-binary @"$read_form" "$base/cgi-bin/api.values.get" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then log "$name=READ_TRANSPORT_FAILED|curl_rc=$rc|login_http_version=$login_ver"; return; fi

  local read_http="${meta%%|*}" read_ver="${meta#*|}" read_resp p208_has p208_type p208_is_null p208
  read_resp=$(json_field "$read_body" '.response')
  p208_has=$(jq -r 'if (.body|type)=="object" and (.body|has("P208")) then "YES" else "NO" end' "$read_body" 2>/dev/null || echo NO)
  p208_type=$(jq -r 'if (.body|type)=="object" and (.body|has("P208")) then (.body.P208|type) else "ABSENT" end' "$read_body" 2>/dev/null || echo INVALID)
  p208_is_null=$(jq -r 'if (.body|type)=="object" and (.body|has("P208")) and (.body.P208==null) then "YES" else "NO" end' "$read_body" 2>/dev/null || echo UNKNOWN)

  if [ "$read_http" != 200 ] || [ "$read_resp" != success ] || [ "$p208_has" != YES ]; then
    log "$name=READ_FAILED|read_http=$read_http|read_http_version=$read_ver|read_response=${read_resp:-EMPTY}|p208_key_present=$p208_has|p208_type=$p208_type|p208_is_null=$p208_is_null|set_cookie_count=$cookie_count"
    return
  fi
  if [ "$p208_is_null" = YES ]; then
    log "$name=WRITE_SKIPPED_NULL|read=SUCCESS|p208_key_present=YES|p208_type=$p208_type|set_cookie_count=$cookie_count"
    return
  fi

  # Extract the exact current scalar value only into process memory; never print it.
  p208=$(jq -r '.body.P208 | if type=="string" then . elif type=="number" or type=="boolean" then tostring else empty end' "$read_body" 2>/dev/null || true)
  if [ "$p208_type" != string ] && [ "$p208_type" != number ] && [ "$p208_type" != boolean ]; then
    log "$name=WRITE_SKIPPED_UNSUPPORTED_TYPE|p208_key_present=YES|p208_type=$p208_type|set_cookie_count=$cookie_count"
    return
  fi

  make_form write "$write_form" "$p208" "$sid"
  set +e
  meta=$(curl "${common[@]}" -D "$write_hdr" -b "$cookie" -c "$cookie" -o "$write_body" -w '%{http_code}|%{http_version}' --data-binary @"$write_form" "$base/cgi-bin/api.values.post" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then log "$name=WRITE_TRANSPORT_FAILED|curl_rc=$rc|read_http_version=$read_ver"; return; fi

  local post_http="${meta%%|*}" post_ver="${meta#*|}" post_resp post_status diagnostic
  post_resp=$(json_field "$write_body" '.response')
  post_status=$(json_field "$write_body" '.body.status')
  diagnostic=WRITE_REJECTED_OTHER
  if [ "$post_http" = 200 ] && [ "$post_resp" = success ]; then diagnostic=WRITE_ACCEPTED; fi
  if [ "$post_status" = session-expired ]; then diagnostic=WRITE_SESSION_EXPIRED; fi

  log "$name=$diagnostic|login=SUCCESS|set_cookie_count=$cookie_count|read=SUCCESS|p208_key_present=YES|p208_type=$p208_type|p208_is_null=NO|post_http=$post_http|post_http_version=$post_ver|post_response=${post_resp:-EMPTY}|post_status=${post_status:-EMPTY}"
}

log '=== G10-18F GRANDSTREAM P208 KEY-AWARE WRITE PROOF ==='
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=SAME-VALUE-P208-ONLY_AFTER_KEY-PRESENCE-READ'
log 'credential_values_logged=NO'
log 'session_values_logged=NO'
log 'p208_value_logged=NO'
log 'basis=G10-18D_PROVED_P208_KEY_PRESENT_AND_G10-18E_EXPOSED_EMPTY-VALUE-GUARD_BUG'

run_case lan_http11_cookie "http://$PHONE_IP" --http1.1
run_case tunnel_http2_cookie "https://$TUNNEL_HOST" --http2

log 'G10-18F-COMPLETE'
