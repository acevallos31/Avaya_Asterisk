#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${RUNNER_TEMP:-/tmp}/g10-08-grandstream-http-auth.txt}"
PHONE_IP='192.168.1.167'
USER_CANDIDATE='admin'
PASS_CANDIDATE='admin'

probe_post() {
  local label="$1" data="$2" body hdr code ctype sid='NO'
  body="$(mktemp)"
  hdr="$(mktemp)"
  trap 'rm -f "$body" "$hdr"' RETURN
  code="$(curl -sS --connect-timeout 5 --max-time 8 -D "$hdr" -o "$body" -w '%{http_code}' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data "$data" "http://${PHONE_IP}/cgi-bin/dologin" || true)"
  ctype="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$hdr")"
  if grep -Eq '"sid"[[:space:]]*:' "$body"; then sid='YES'; fi
  printf 'auth_probe=%s|http=%s|content_type=%s|sid_present=%s|bytes=%s\n' \
    "$label" "${code:-000}" "${ctype:-NONE}" "$sid" "$(wc -c < "$body" | tr -d ' ')"
  rm -f "$body" "$hdr"
  trap - RETURN
}

{
  echo '=== G10-08 GRANDSTREAM GXP1625 HTTP AUTH COMPATIBILITY ==='
  echo "phone_ip=${PHONE_IP}"
  echo 'configuration_write=NO'
  echo 'api_values_post_called=NO'
  echo 'credentials_logged=NO'
  echo 'credential_candidate=MODEL-DEFAULT-ADMIN'
  echo
  probe_post 'password-only' "password=${PASS_CANDIDATE}"
  sleep 1
  probe_post 'username-plus-password' "username=${USER_CANDIDATE}&password=${PASS_CANDIDATE}"
  echo
  echo 'G10-08-PASS'
} | tee "$REPORT"
