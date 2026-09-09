#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/endpoint-lab"
COLLECTION="${ROOT}/collections/gxp1625.postman_collection.json"
REPORT_DIR="${ROOT}/reports"
BASE_URL="${BASE_URL:-http://192.168.1.167}"
HTTP_USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"

mkdir -p "$REPORT_DIR"

if [[ ! -f "$COLLECTION" ]]; then
  echo "ERROR: collection not found: $COLLECTION" >&2
  exit 2
fi

read -rsp "Grandstream web password: " HTTP_PASSWORD
echo

TMP_ENV="$(mktemp)"
chmod 600 "$TMP_ENV"
cleanup() {
  rm -f "$TMP_ENV"
  unset HTTP_PASSWORD
}
trap cleanup EXIT

python3 - "$TMP_ENV" "$BASE_URL" "$HTTP_USERNAME" "$HTTP_PASSWORD" <<'PY'
import json, sys
path, base_url, username, password = sys.argv[1:]
origin = base_url.rstrip('/')
referer = origin + '/'
env = {
  "id": "gxp1625-local-lab",
  "name": "GXP1625 Local Lab (ephemeral)",
  "values": [
    {"key":"base_url","value":base_url,"enabled":True},
    {"key":"origin","value":origin,"enabled":True},
    {"key":"referer","value":referer,"enabled":True},
    {"key":"http_username","value":username,"enabled":True},
    {"key":"http_password","value":password,"enabled":True},
    {"key":"sid","value":"","enabled":True},
    {"key":"p208_current","value":"","enabled":True},
    {"key":"write_status","value":"","enabled":True}
  ],
  "_postman_variable_scope": "environment"
}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(env, f)
PY

STAMP="$(date +%Y%m%d-%H%M%S)"
RAW_REPORT="${REPORT_DIR}/gxp1625-newman-${STAMP}.json"
SANITIZED_REPORT="${REPORT_DIR}/gxp1625-newman-${STAMP}-sanitized.json"

set +e
newman run "$COLLECTION" -e "$TMP_ENV" -r cli,json --reporter-json-export "$RAW_REPORT"
NEWMAN_RC=$?
set -e

python3 - "$RAW_REPORT" "$SANITIZED_REPORT" "$BASE_URL" "$NEWMAN_RC" <<'PY'
import json, sys
src, dst, base_url, rc = sys.argv[1:]
with open(src, 'r', encoding='utf-8') as f:
    data = json.load(f)
executions = []
for ex in data.get('run', {}).get('executions', []):
    item = ex.get('item', {}).get('name', '')
    resp = ex.get('response') or {}
    code = resp.get('code')
    assertions = []
    for a in ex.get('assertions') or []:
        assertions.append({
            'assertion': a.get('assertion',''),
            'passed': 'error' not in a
        })
    executions.append({'item': item, 'http_code': code, 'assertions': assertions})
out = {
    'target': base_url,
    'newman_exit_code': int(rc),
    'db_write': 'NO',
    'live_code_write': 'NO',
    'phone_write': 'SAME-VALUE-P208-ONLY',
    'secret_values_logged': 'NO',
    'session_values_logged': 'NO',
    'executions': executions
}
with open(dst, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
PY

rm -f "$RAW_REPORT"

echo
echo "Sanitized report: $SANITIZED_REPORT"
echo "Newman exit code: $NEWMAN_RC"
exit 0
