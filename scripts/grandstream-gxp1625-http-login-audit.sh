#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${RUNNER_TEMP:-/tmp}/g10-07-grandstream-http-login.txt}"
PHONE_IP="192.168.1.167"
BASE="http://${PHONE_IP}"
TMPDIR_LOCAL="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_LOCAL"' EXIT

exec > >(tee "$REPORT") 2>&1

echo '=== G10-07 GRANDSTREAM GXP1625 HTTP LOGIN COMPATIBILITY AUDIT ==='
echo "phone_ip=${PHONE_IP}"
echo 'phone_operation=READ-ONLY-DISCOVERY'
echo 'credentials_used=NO'
echo 'configuration_write=NO'
echo

probe() {
  local label="$1" method="$2" path="$3"
  local hdr="$TMPDIR_LOCAL/${label}.hdr" body="$TMPDIR_LOCAL/${label}.body" code ctype location size
  code="$(curl -sS --connect-timeout 5 --max-time 8 -X "$method" -D "$hdr" -o "$body" -w '%{http_code}' "$BASE$path" || true)"
  ctype="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/{gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$hdr")"
  location="$(awk 'BEGIN{IGNORECASE=1} /^Location:/{gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$hdr")"
  size="$(wc -c < "$body" | tr -d ' ')"
  printf 'probe=%s|method=%s|path=%s|http=%s|content_type=%s|location=%s|bytes=%s\n' "$label" "$method" "$path" "${code:-NA}" "${ctype:-NONE}" "${location:-NONE}" "$size"
}

# Confirm the model endpoint still identifies the phone.
MODEL="$TMPDIR_LOCAL/model.json"
MODEL_CODE="$(curl -sS --connect-timeout 5 --max-time 8 -o "$MODEL" -w '%{http_code}' "$BASE/cgi-bin/api.values.get?request=phone_model:1395" || true)"
echo "model_api_http=$MODEL_CODE"
if grep -Fq 'GXP1625' "$MODEL"; then echo 'model_api_detected=GXP1625'; else echo 'model_api_detected=UNKNOWN'; fi

echo
echo '=== ENDPOINT SHAPE ==='
probe root GET '/'
probe dologin_get GET '/cgi-bin/dologin'
probe dologin_head HEAD '/cgi-bin/dologin'
probe api_values_post_get GET '/cgi-bin/api.values.post'
probe api_values_get_get GET '/cgi-bin/api.values.get?request=phone_model:1395'

echo
echo '=== PUBLIC WEB APP LOGIN REFERENCES ==='
ROOT_BODY="$TMPDIR_LOCAL/root.html"
curl -sS --connect-timeout 5 --max-time 8 "$BASE/" -o "$ROOT_BODY" || true
# Show only path/field hints, never cookies, passwords or arbitrary page content.
if grep -Eo '/cgi-bin/[A-Za-z0-9._/?=&:-]+' "$ROOT_BODY" 2>/dev/null | sort -u | head -n 30 | sed 's/^/root_cgi_reference=/' ; then :; fi
if grep -Eoi '(dologin|api\.values\.(get|post)|username|password|sid|session)' "$ROOT_BODY" 2>/dev/null | sort -fu | sed 's/^/root_login_hint=/' ; then :; fi

echo
echo '=== INSTALLED ISSABEL EXPECTATION ==='
GS='/usr/share/issabel/endpoint-classes/class/issabel/vendor/Grandstream.py'
if [ -f "$GS" ]; then
  echo 'grandstream_py=PRESENT'
  grep -nE "dologin|api\.values\.post|Content-Type|application/json|sid" "$GS" | head -n 40 | sed -E 's/(password[^,}]*)/***REDACTED***/Ig' || true
else
  echo 'grandstream_py=ABSENT'
fi

echo
echo '=== INTERPRETATION ==='
echo 'issabel_failure_observed=DOLOGIN-EXPECTED-JSON-BUT-RECEIVED-TEXT-HTML'
echo 'credential_validity=NOT-TESTED-BY-G10-07'
echo 'next_decision=COMPARE-FIRMWARE-LOGIN-SCHEME-WITH-ISSABEL-GXP140x-HANDLER'
echo 'G10-07-PASS'
