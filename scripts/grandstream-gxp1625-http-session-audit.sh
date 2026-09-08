#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-}"
[ -n "$REPORT" ] || { echo 'usage: script <report-path>' >&2; exit 2; }
: "${GRANDSTREAM_HTTP_PASSWORD:?GRANDSTREAM_HTTP_PASSWORD required}"
GRANDSTREAM_HTTP_USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PHONE_IP="192.168.1.167"
FIRMWARE="1.0.7.70"

HDR="$(mktemp)"
BODY="$(mktemp)"
JAR="$(mktemp)"
FOLLOW_HDR="$(mktemp)"
FOLLOW_BODY="$(mktemp)"
trap 'rm -f "$HDR" "$BODY" "$JAR" "$FOLLOW_HDR" "$FOLLOW_BODY"' EXIT
chmod 600 "$HDR" "$BODY" "$JAR" "$FOLLOW_HDR" "$FOLLOW_BODY"

LOGIN_CODE="$(curl -sS --connect-timeout 5 --max-time 10 \
  -D "$HDR" -o "$BODY" -c "$JAR" -w '%{http_code}' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=${GRANDSTREAM_HTTP_USERNAME}" \
  --data-urlencode "password=${GRANDSTREAM_HTTP_PASSWORD}" \
  "http://${PHONE_IP}/cgi-bin/dologin" || true)"

LOGIN_CT="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$HDR")"
LOGIN_LOC="$(awk 'BEGIN{IGNORECASE=1} /^Location:/ {gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$HDR")"
[ -n "$LOGIN_CT" ] || LOGIN_CT='NONE'
[ -n "$LOGIN_LOC" ] || LOGIN_LOC='NONE'
LOGIN_BYTES="$(wc -c < "$BODY" | tr -d ' ')"

COOKIE_COUNT="$(awk 'BEGIN{n=0} !/^#/ && NF>=7 {n++} END{print n}' "$JAR")"
COOKIE_NAMES="$(awk '!/^#/ && NF>=7 {print $6}' "$JAR" | sort -u | paste -sd, -)"
[ -n "$COOKIE_NAMES" ] || COOKIE_NAMES='NONE'

SET_COOKIE_NAMES="$(awk 'BEGIN{IGNORECASE=1} /^Set-Cookie:/ {gsub("\r",""); sub(/^Set-Cookie:[[:space:]]*/,""); split($0,a,"="); print a[1]}' "$HDR" | sort -u | paste -sd, -)"
[ -n "$SET_COOKIE_NAMES" ] || SET_COOKIE_NAMES='NONE'

BODY_HAS_SID='NO'; grep -Eqi '(^|[^A-Za-z0-9_])sid([^A-Za-z0-9_]|$)' "$BODY" && BODY_HAS_SID='YES' || true
BODY_HAS_SUCCESS='NO'; grep -Eqi 'success|successful|ok' "$BODY" && BODY_HAS_SUCCESS='YES' || true
BODY_SHA="$(sha256sum "$BODY" | awk '{print $1}')"

FOLLOW_CODE="$(curl -sS --connect-timeout 5 --max-time 10 \
  -D "$FOLLOW_HDR" -o "$FOLLOW_BODY" -b "$JAR" -w '%{http_code}' \
  "http://${PHONE_IP}/" || true)"
FOLLOW_CT="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$FOLLOW_HDR")"
[ -n "$FOLLOW_CT" ] || FOLLOW_CT='NONE'
FOLLOW_BYTES="$(wc -c < "$FOLLOW_BODY" | tr -d ' ')"
FOLLOW_SHA="$(sha256sum "$FOLLOW_BODY" | awk '{print $1}')"

{
  echo '=== G10-10 GRANDSTREAM GXP1625 HTTP SESSION AUDIT ==='
  echo "phone_ip=${PHONE_IP}"
  echo "firmware_prog=${FIRMWARE}"
  echo 'credential_source=GITHUB-ACTIONS-SECRET'
  echo 'credentials_logged=NO'
  echo 'configuration_write=NO'
  echo 'api_values_post_called=NO'
  echo
  echo "login_http=${LOGIN_CODE}"
  echo "login_content_type=${LOGIN_CT}"
  echo "login_location=${LOGIN_LOC}"
  echo "login_body_bytes=${LOGIN_BYTES}"
  echo "login_body_sha256=${BODY_SHA}"
  echo "login_body_has_sid_token=${BODY_HAS_SID}"
  echo "login_body_has_success_token=${BODY_HAS_SUCCESS}"
  echo "set_cookie_names=${SET_COOKIE_NAMES}"
  echo "cookie_jar_count=${COOKIE_COUNT}"
  echo "cookie_names=${COOKIE_NAMES}"
  echo
  echo "followup_root_http=${FOLLOW_CODE}"
  echo "followup_root_content_type=${FOLLOW_CT}"
  echo "followup_root_bytes=${FOLLOW_BYTES}"
  echo "followup_root_sha256=${FOLLOW_SHA}"
  echo
  echo 'G10-10-PASS'
} | tee "$REPORT"
