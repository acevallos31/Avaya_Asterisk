#!/usr/bin/env bash
set -euo pipefail

PHONE_IP="${PHONE_IP:-192.168.1.167}"
TUNNEL_HOST="${TUNNEL_HOST:-phone1.nocpbx.com}"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"
REPORT="${1:-g10-18b-login-fidelity-matrix.txt}"

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

run_login() {
  local name="$1" url="$2" proto="$3" mode="$4"
  local base="${url%/cgi-bin/dologin}"
  local body="$TMP/$name.form" out="$TMP/$name.body" hdr="$TMP/$name.hdr"
  make_form "$body"
  local body_len
  body_len=$(wc -c < "$body" | tr -d ' ')

  local args=( -sS "$proto" --connect-timeout 5 --max-time 20 -D "$hdr" -o "$out" -w '%{http_code}|%{http_version}'
    -H 'Accept: */*' -H 'Content-Type: application/x-www-form-urlencoded' )

  case "$mode" in
    minimal) ;;
    host_referer)
      args+=( -H "Referer: $base/" )
      ;;
    browser)
      args+=( -H "Origin: $base" -H "Referer: $base/"
        -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36' )
      ;;
  esac

  local meta rc
  set +e
  meta=$(curl "${args[@]}" --data-binary @"$body" "$url" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=TRANSPORT_FAILED|curl_rc=$rc|form_len=$body_len"
    return
  fi

  local http="${meta%%|*}" ver="${meta#*|}" response sid ctype
  response=$(json_field "$out" '.response')
  sid=$(json_field "$out" '.body.sid')
  ctype=$(awk 'BEGIN{IGNORECASE=1} /^content-type:/{sub(/\r$/,""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$hdr" || true)
  log "$name=$( [ "$http" = 200 ] && [ "$response" = success ] && [ -n "$sid" ] && echo LOGIN_ACCEPTED || echo LOGIN_REJECTED )|http=$http|http_version=$ver|response=${response:-EMPTY}|sid_present=$( [ -n "$sid" ] && echo YES || echo NO )|form_len=$body_len|content_type=${ctype:-EMPTY}"
}

log '=== G10-18B GRANDSTREAM LOGIN FIDELITY MATRIX ==='
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=NO'
log 'credential_values_logged=NO'
log 'session_values_logged=NO'
log 'purpose=ISOLATE_LOGIN_REQUEST_FIDELITY'

run_login lan_minimal "http://$PHONE_IP/cgi-bin/dologin" --http1.1 minimal
run_login lan_host_referer "http://$PHONE_IP/cgi-bin/dologin" --http1.1 host_referer
run_login lan_browser "http://$PHONE_IP/cgi-bin/dologin" --http1.1 browser
run_login tunnel_http11_browser "https://$TUNNEL_HOST/cgi-bin/dologin" --http1.1 browser
run_login tunnel_http2_browser "https://$TUNNEL_HOST/cgi-bin/dologin" --http2 browser
run_login tunnel_http3_browser "https://$TUNNEL_HOST/cgi-bin/dologin" --http3 browser

log 'G10-18B-COMPLETE'
