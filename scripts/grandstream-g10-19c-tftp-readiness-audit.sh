#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-g10-19c-tftp-readiness-audit.txt}"
CFG='/tftpboot/cfgc074ade86609'
XINETD_TFTP='/etc/xinetd.d/tftp'

: > "$REPORT"
chmod 600 "$REPORT"
log() { printf '%s\n' "${1:-}" | tee -a "$REPORT"; }

log '=== G10-19C GRANDSTREAM TFTP READINESS AUDIT ==='
log 'scope=READ_ONLY'
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=NO'
log 'service_change=NO'
log 'firewall_change=NO'
log 'selinux_change=NO'
log 'cfg_payload_dumped=NO'
log

log '=== CFG READINESS ==='
if [ -e "$CFG" ]; then
  stat -c 'cfg_state=PRESENT|owner=%U|group=%G|mode=%a|size=%s' "$CFG" | tee -a "$REPORT"
  [ -r "$CFG" ] && log 'cfg_readable_by_runner=YES' || log 'cfg_readable_by_runner=NO'
else
  log 'cfg_state=ABSENT'
fi
log

log '=== TFTP PACKAGES / BINARIES ==='
for p in tftp tftp-server xinetd; do
  if rpm -q "$p" >/dev/null 2>&1; then
    ver="$(rpm -q "$p" 2>/dev/null || true)"
    log "package=$p|state=INSTALLED|version=$ver"
  else
    log "package=$p|state=NOT_INSTALLED"
  fi
done
for b in /usr/sbin/in.tftpd /usr/bin/tftp /usr/sbin/xinetd; do
  [ -x "$b" ] && log "binary=$b|state=EXECUTABLE" || log "binary=$b|state=MISSING_OR_NOT_EXECUTABLE"
done
log

log '=== XINETD TFTP CONFIG ==='
if [ -r "$XINETD_TFTP" ]; then
  log 'xinetd_tftp_config=PRESENT'
  awk '
    /^[[:space:]]*#/ {next}
    /^[[:space:]]*(disable|socket_type|protocol|wait|user|server|server_args|per_source|cps)[[:space:]]*=/ {
      gsub(/^[[:space:]]+|[[:space:]]+$/, ""); print "xinetd_tftp_" $0
    }
  ' "$XINETD_TFTP" | sed -E 's/[[:space:]]+/ /g' | tee -a "$REPORT"
else
  log 'xinetd_tftp_config=MISSING_OR_UNREADABLE'
fi
log

log '=== SERVICE STATE ==='
for svc in xinetd tftp tftp.socket tftp.service; do
  active="$(systemctl is-active "$svc" 2>/dev/null || true)"
  enabled="$(systemctl is-enabled "$svc" 2>/dev/null || true)"
  [ -n "$active$enabled" ] && log "service=$svc|active=${active:-unknown}|enabled=${enabled:-unknown}"
done
log

log '=== UDP 69 SOCKET ==='
if command -v ss >/dev/null 2>&1; then
  if ss -lunp 2>/dev/null | awk '{print $5}' | grep -Eq '(^|:)69$'; then
    log 'udp69_listener=YES'
  elif ss -lun 2>/dev/null | awk '{print $5}' | grep -Eq '(^|:)69$'; then
    log 'udp69_listener=YES'
  else
    log 'udp69_listener=NO'
  fi
else
  log 'udp69_listener=UNKNOWN_SS_MISSING'
fi
log

log '=== FIREWALL READINESS ==='
if command -v firewall-cmd >/dev/null 2>&1; then
  fw_state="$(firewall-cmd --state 2>/dev/null || true)"
  log "firewalld_state=${fw_state:-unknown}"
  if [ "$fw_state" = 'running' ]; then
    zones="$(firewall-cmd --get-active-zones 2>/dev/null | awk 'NF==1 {print $1}' | paste -sd, - || true)"
    log "firewalld_active_zones=${zones:-unknown}"
    if firewall-cmd --query-service=tftp >/dev/null 2>&1; then
      log 'firewalld_tftp_service_default_zone=YES'
    else
      log 'firewalld_tftp_service_default_zone=NO_OR_UNAVAILABLE'
    fi
  fi
else
  log 'firewalld_state=COMMAND_MISSING'
fi
log

log '=== SELINUX READINESS ==='
if command -v getenforce >/dev/null 2>&1; then
  log "selinux_mode=$(getenforce 2>/dev/null || echo unknown)"
else
  log 'selinux_mode=GETENFORCE_MISSING'
fi
log

log '=== XINETD LOG HINTS (SANITIZED) ==='
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u xinetd -n 30 --no-pager 2>/dev/null \
    | grep -Ei 'tftp|69|bind|fail|error|disable|start|exit' \
    | tail -n 12 \
    | sed -E 's/[0-9]{1,3}(\.[0-9]{1,3}){3}/IP_REDACTED/g' \
    | sed 's/^/xinetd_log=/' \
    | tee -a "$REPORT" || true
fi
log

log '=== DECISION ==='
disable_value='UNKNOWN'
if [ -r "$XINETD_TFTP" ]; then
  disable_value="$(awk -F= '/^[[:space:]]*disable[[:space:]]*=/{gsub(/[[:space:]]/,"",$2); print tolower($2); exit}' "$XINETD_TFTP")"
  [ -z "$disable_value" ] && disable_value='UNSET'
fi
log "xinetd_tftp_disable=$disable_value"
if [ "$disable_value" = 'yes' ]; then
  log 'diagnostic=TFTP_DISABLED_IN_XINETD'
elif [ "$disable_value" = 'no' ]; then
  if ss -lun 2>/dev/null | awk '{print $5}' | grep -Eq '(^|:)69$'; then
    log 'diagnostic=TFTP_LISTENER_READY'
  else
    log 'diagnostic=TFTP_ENABLED_BUT_NO_UDP69_LISTENER'
  fi
else
  log 'diagnostic=TFTP_CONFIG_STATE_UNRESOLVED'
fi
log 'next_activity=G10-19D_TFTP_ENABLE_OR_REPAIR_CONTROLLED'
log 'G10-19C-COMPLETE'
