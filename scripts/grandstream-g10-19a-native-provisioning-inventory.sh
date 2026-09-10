#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-g10-19a-native-provisioning-inventory.txt}"
PHONE_MAC_COMPACT="c074ade86609"
CFG_BIN="/tftpboot/cfg${PHONE_MAC_COMPACT}"
CFG_XML="/tftpboot/cfg${PHONE_MAC_COMPACT}.xml"
PY_CLASS="/usr/share/issabel/endpoint-classes/class/issabel/vendor/Grandstream.py"
PHP_CLASS="/var/www/html/modules/endpoint_configurator/phonesrv/vendor/Grandstream.class.php"

: > "$REPORT"
chmod 600 "$REPORT"
log() { printf '%s\n' "${1:-}" | tee -a "$REPORT"; }

log '=== G10-19A GRANDSTREAM NATIVE PROVISIONING INVENTORY ==='
log 'scope=READ_ONLY'
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=NO'
log 'cfg_content_logged=NO'
log 'sip_secret_logged=NO'
log 'target_model=GXP1625'
log 'target_firmware=1.0.7.70'
log 'target_account=202'
log

log '=== ENDPOINT CONFIGURATOR MODEL STATE ==='
if sudo -n /usr/local/sbin/avaya-j129-lab-deploy inspect-manufacturer Grandstream GXP1625 C0:74:AD 2>&1 \
    | sed -E 's/(password|secret|passwd|pwd)[^[:space:]]*/\1=REDACTED/Ig' \
    | tee -a "$REPORT" >/dev/null; then
  log 'manufacturer_inventory=PASS'
else
  log 'manufacturer_inventory=FAILED'
fi
log

log '=== STOCK IMPLEMENTATION FILES ==='
for f in "$PY_CLASS" "$PHP_CLASS"; do
  if [ -f "$f" ]; then
    stat -c 'source_file=%n|owner=%U|group=%G|mode=%a|size=%s|mtime=%y' "$f" | tee -a "$REPORT"
    sha256sum "$f" | awk '{print "source_sha256=" $1}' | tee -a "$REPORT"
  else
    log "source_file_missing=$f"
  fi
done
log

log '=== GRANDSTREAM.PY PROVISIONING SYMBOL MAP ==='
if [ -f "$PY_CLASS" ]; then
  python3 - "$PY_CLASS" <<'PY' | tee -a "$REPORT"
import re, sys
path=sys.argv[1]
need=(
    r'^\s*def\s+(updateLocalConfig|_enableStaticProvisioning|prepareConfiguration|writeConfig|createConfigFile)\b',
    r'\bP212\b', r'\bP237\b', r'\bP240\b', r'\bP1359\b',
    r'cfg.*mac', r'tftp', r'provision',
)
rx=[re.compile(x,re.I) for x in need]
with open(path, encoding='utf-8', errors='replace') as fh:
    for n,line in enumerate(fh,1):
        # Only static source lines relevant to provisioning; never dump runtime cfg.
        if any(r.search(line) for r in rx):
            s=line.rstrip('\n')
            # Defensive redaction of obvious literal credential assignments.
            s=re.sub(r'(?i)(password|secret|passwd|pwd)\s*=\s*[^,}\]]+', r'\1=REDACTED', s)
            print(f'py_line={n}|{s.strip()}')
PY
else
  log 'py_symbol_map=SKIPPED-MISSING-FILE'
fi
log

log '=== PHP GRANDSTREAM INTEGRATION SYMBOL MAP ==='
if [ -f "$PHP_CLASS" ]; then
  python3 - "$PHP_CLASS" <<'PY' | tee -a "$REPORT"
import re, sys
path=sys.argv[1]
rx=[re.compile(x,re.I) for x in (r'Grandstream',r'cfg',r'tftp',r'provision',r'updateLocalConfig')]
with open(path, encoding='utf-8', errors='replace') as fh:
    for n,line in enumerate(fh,1):
        if any(r.search(line) for r in rx):
            s=line.rstrip('\n')
            s=re.sub(r'(?i)(password|secret|passwd|pwd)\s*=\s*[^,;)}]+', r'\1=REDACTED', s)
            print(f'php_line={n}|{s.strip()}')
PY
else
  log 'php_symbol_map=SKIPPED-MISSING-FILE'
fi
log

log '=== GENERATED CFG INVENTORY (METADATA ONLY) ==='
for f in "$CFG_BIN" "$CFG_XML"; do
  if [ -e "$f" ]; then
    stat -c 'cfg_file=%n|state=PRESENT|owner=%U|group=%G|mode=%a|size=%s|mtime=%y' "$f" | tee -a "$REPORT"
    sha256sum "$f" | awk -v n="$(basename "$f")" '{print "cfg_sha256=" $1 "|file=" n}' | tee -a "$REPORT"
    file -b "$f" | sed 's/^/cfg_file_type=/' | tee -a "$REPORT"
  else
    log "cfg_file=$f|state=ABSENT"
  fi
done
log 'cfg_payload_dumped=NO'
log

log '=== TFTP / PROVISIONING SERVICE INVENTORY ==='
if command -v ss >/dev/null 2>&1; then
  if ss -lun 2>/dev/null | awk '{print $5}' | grep -Eq '(^|:)69$'; then
    log 'udp69_listener=YES'
  else
    log 'udp69_listener=NO'
  fi
else
  log 'udp69_listener=UNKNOWN-SS-MISSING'
fi
for svc in tftp tftp.socket tftp.service xinetd; do
  if systemctl list-unit-files "$svc" >/dev/null 2>&1; then
    state="$(systemctl is-active "$svc" 2>/dev/null || true)"
    enabled="$(systemctl is-enabled "$svc" 2>/dev/null || true)"
    log "service=$svc|active=${state:-unknown}|enabled=${enabled:-unknown}"
  fi
done
log

log '=== G10-19A DECISION INPUTS ==='
[ -f "$CFG_BIN" ] && log 'existing_binary_cfg=YES' || log 'existing_binary_cfg=NO'
[ -f "$CFG_XML" ] && log 'existing_xml_cfg=YES' || log 'existing_xml_cfg=NO'
if [ -f "$PY_CLASS" ] && grep -Eq '\bP212\b' "$PY_CLASS"; then log 'stock_py_mentions_P212=YES'; else log 'stock_py_mentions_P212=NO'; fi
if [ -f "$PY_CLASS" ] && grep -Eq '\bP237\b' "$PY_CLASS"; then log 'stock_py_mentions_P237=YES'; else log 'stock_py_mentions_P237=NO'; fi
log 'next_activity=G10-19B_OFFICIAL_PVALUE_MAP'
log 'G10-19A-COMPLETE'
