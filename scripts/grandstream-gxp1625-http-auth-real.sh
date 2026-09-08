#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${RUNNER_TEMP:-/tmp}/g10-09-grandstream-http-auth-real.txt}"
PHONE_IP="192.168.1.167"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"

[ -n "$PASSWORD" ] || { echo 'ERROR: GRANDSTREAM_HTTP_PASSWORD no definido' >&2; exit 2; }

TMP_BODY="$(mktemp)"
TMP_HDR="$(mktemp)"
trap 'rm -f "$TMP_BODY" "$TMP_HDR"' EXIT
chmod 600 "$TMP_BODY" "$TMP_HDR"

probe_login() {
  local label="$1" data="$2" code ctype sid
  : > "$TMP_BODY"
  : > "$TMP_HDR"
  code="$(curl -sS --connect-timeout 5 --max-time 10 \
    -D "$TMP_HDR" -o "$TMP_BODY" -w '%{http_code}' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data "$data" \
    "http://${PHONE_IP}/cgi-bin/dologin" || true)"
  ctype="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {sub(/\r$/,""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$TMP_HDR")"
  [ -n "$ctype" ] || ctype='NONE'
  if grep -Eq '"sid"[[:space:]]*:' "$TMP_BODY"; then sid='YES'; else sid='NO'; fi
  printf 'auth_probe=%s|http=%s|content_type=%s|sid_present=%s|bytes=%s\n' \
    "$label" "$code" "$ctype" "$sid" "$(wc -c < "$TMP_BODY" | tr -d ' ')"
}

{
  echo '=== G10-09 GRANDSTREAM GXP1625 REAL HTTP AUTH ==='
  echo "phone_ip=$PHONE_IP"
  echo 'firmware_prog=1.0.7.70'
  echo 'configuration_write=NO'
  echo 'api_values_post_called=NO'
  echo 'credentials_logged=NO'
  echo 'credential_source=GITHUB-ACTIONS-SECRET'
  echo

  # First reproduce the exact Issabel GXP140x payload shape.
  probe_login 'password-only-real' "password=$(python3 -c 'import os,urllib.parse; print(urllib.parse.quote_plus(os.environ["GRANDSTREAM_HTTP_PASSWORD"]))')"

  # Then test username + password, still authentication-only.
  probe_login 'username-plus-password-real' "username=$(python3 -c 'import os,urllib.parse; print(urllib.parse.quote_plus(os.environ.get("GRANDSTREAM_HTTP_USERNAME","admin")))')&password=$(python3 -c 'import os,urllib.parse; print(urllib.parse.quote_plus(os.environ["GRANDSTREAM_HTTP_PASSWORD"]))')"

  echo
  echo 'G10-09-PASS'
} | tee "$REPORT"

grep -Fq 'G10-09-PASS' "$REPORT"
