#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${RUNNER_TEMP:-/tmp}/grandstream-gxp1625-native-preflight.txt}"
PHONE_IP='192.168.1.167'
PHONE_MAC='C0:74:AD:E8:66:09'
OUI='C0:74:AD'
EXPECTED_MODEL='GXP1625'
CFG_FILE='/tftpboot/cfgc074ade86609'
HELPER='/usr/local/sbin/avaya-j129-lab-deploy'
GRANDSTREAM_PY='/usr/share/issabel/endpoint-classes/class/issabel/vendor/Grandstream.py'

mkdir -p "$(dirname "$REPORT")"
: > "$REPORT"

log() {
  printf '%s\n' "$*" | tee -a "$REPORT"
}

log '=== G10-04 GRANDSTREAM GXP1625 NATIVE PROVISIONING PREFLIGHT ==='
log "phone_ip=$PHONE_IP"
log "phone_mac=$PHONE_MAC"
log "oui=$OUI"
log "expected_model=$EXPECTED_MODEL"
log 'sip_registration_baseline=MANUAL-USER-CONFIRMED'
log 'endpointconfig_provisioning=NOT-YET-VALIDATED'
log 'db_operation=READ-ONLY'
log 'phone_operation=READ-ONLY-HTTP-GET'
log

log '=== 1. LIVE ENDPOINTCONFIG DB / NATIVE GRANDSTREAM SUPPORT ==='
DB_TMP="$(mktemp)"
trap 'rm -f "$DB_TMP"' EXIT
sudo -n "$HELPER" inspect-manufacturer Grandstream "$EXPECTED_MODEL" "$OUI" | tee "$DB_TMP" | tee -a "$REPORT"

grep -Fq 'MANUFACTURER-DB-READONLY-PASS' "$DB_TMP"
grep -Fq $'10\tGrandstream\tGrandstream' "$DB_TMP"
grep -Fq $'134\t10\tGXP1625\tGXP1625' "$DB_TMP"
awk '/=== REQUESTED PREFIX LOOKUP ===/{f=1;next}/=== ENDPOINT COUNT ===/{f=0} f && $0 ~ /C0:74:AD/ && $0 ~ /Grandstream/ {found=1} END{exit !found}' "$DB_TMP"

ENDPOINT_COUNT="$(awk '/=== ENDPOINT COUNT ===/{f=1;next} f && $0 ~ /^[0-9]+$/ {print $0; exit}' "$DB_TMP" | tr -d '\r')"
if [[ "$ENDPOINT_COUNT" =~ ^[0-9]+$ ]] && [ "$ENDPOINT_COUNT" -ge 1 ]; then
  log "endpointconfig_grandstream_count=$ENDPOINT_COUNT"
  log 'endpoint_discovery_state=PRESENT'
else
  log "endpointconfig_grandstream_count=${ENDPOINT_COUNT:-UNKNOWN}"
  log 'endpoint_discovery_state=NOT-CONFIRMED'
  exit 1
fi

log
log '=== 2. INSTALLED ISSABEL GRANDSTREAM HANDLER ==='
if [ -r "$GRANDSTREAM_PY" ]; then
  log "grandstream_handler=$GRANDSTREAM_PY"
  sha256sum "$GRANDSTREAM_PY" | tee -a "$REPORT"
  grep -Fq 'def probeModel' "$GRANDSTREAM_PY"
  grep -Fq 'def updateLocalConfig' "$GRANDSTREAM_PY"
  grep -Fq '_encodeGrandstreamConfig' "$GRANDSTREAM_PY"
  grep -Fq '_enableStaticProvisioning' "$GRANDSTREAM_PY"
  grep -Fq '/cgi-bin/api.values.get?request=phone_model:1395' "$GRANDSTREAM_PY"
  log 'native_grandstream_handler=PASS'
else
  log 'native_grandstream_handler=FAIL'
  exit 1
fi

log
log '=== 3. PREEXISTING NATIVE CONFIG FILE STATE ==='
if [ -e "$CFG_FILE" ]; then
  log 'cfg_file_state=PREEXISTING'
  stat -c 'cfg_file=%n owner=%U group=%G mode=%a size=%s mtime=%y' "$CFG_FILE" 2>/dev/null | tee -a "$REPORT" || true
else
  log 'cfg_file_state=ABSENT'
  log "expected_cfg_file=$CFG_FILE"
fi

log
log '=== 4. PHONE MODEL API (READ ONLY) ==='
command -v curl >/dev/null 2>&1 || { log 'curl=NOT-AVAILABLE'; exit 1; }
MODEL_BODY="$(mktemp)"
trap 'rm -f "$DB_TMP" "$MODEL_BODY"' EXIT
MODEL_HTTP="$(curl --connect-timeout 3 --max-time 6 -sS -o "$MODEL_BODY" -w '%{http_code}' "http://${PHONE_IP}/cgi-bin/api.values.get?request=phone_model:1395" || true)"
log "model_api_http=$MODEL_HTTP"
if [ "$MODEL_HTTP" != '200' ]; then
  log 'model_api=FAIL'
  exit 1
fi
DETECTED_MODEL="$(sed -n 's/.*"phone_model"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MODEL_BODY" | head -n1)"
log "model_api_detected=${DETECTED_MODEL:-UNKNOWN}"
[ "$DETECTED_MODEL" = "$EXPECTED_MODEL" ] || { log 'model_api=FAIL'; exit 1; }
log 'model_api=PASS'

log
log '=== 5. STATIC PROVISIONING INTERFACE PROBE (READ-ONLY GET ONLY) ==='
probe_http() {
  local label="$1" path="$2" meta
  meta="$(curl --connect-timeout 2 --max-time 4 -sS -o /dev/null -w '%{http_code}|%{content_type}|%{size_download}' "http://${PHONE_IP}${path}" || true)"
  log "provision_probe=${label}|${path}|${meta:-REQUEST-FAILED}"
}
probe_http 'GXP140x-JSON' '/cgi-bin/api.values.post'
probe_http 'BT200' '/update.htm'
probe_http 'GXVxxxx' '/manager'
probe_http 'GXP1450' '/cgi-bin/update'

log
log '=== 6. INTERPRETATION GUARDRAILS ==='
log 'sip_registration_evidence=DO-NOT-COUNT-AS-ENDPOINTCONFIG-SUCCESS'
log 'sip_registration_origin=MANUAL'
log 'configure_button=NOT-USED-BY-THIS-TEST'
log 'grandstream_py_modified=NO'
log 'phone_rebooted=NO'
log 'phone_config_changed=NO'
log 'G10-04-PREFLIGHT-PASS'
