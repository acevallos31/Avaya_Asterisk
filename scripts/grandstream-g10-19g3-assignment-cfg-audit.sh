#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-g10-19g3-assignment-cfg-audit.txt}"
MAC="C0:74:AD:E8:66:09"
CFG="/tftpboot/cfgc074ade86609"
AMPORTAL="/etc/amportal.conf"
: > "$REPORT"
chmod 600 "$REPORT"
log(){ printf '%s\n' "$1" | tee -a "$REPORT"; }

log 'scope=READ_ONLY_ASSIGNMENT_AND_CFG_AUDIT'
log 'db_write=NO'
log 'phone_write=NO'
log 'pbx_live_code_write=NO'
log 'cfg_payload_dumped=NO'
log 'sip_secret_logged=NO'

if [ -e "$CFG" ]; then
  stat -c 'cfg_state=PRESENT|owner=%U|group=%G|mode=%a|size=%s|mtime_epoch=%Y|mtime=%y' "$CFG" | tee -a "$REPORT"
  sha256sum "$CFG" | awk '{print "cfg_sha256=" $1}' | tee -a "$REPORT"
else
  log 'cfg_state=ABSENT'
fi

if [ ! -r "$AMPORTAL" ]; then
  log 'db_audit=BLOCKED_AMPORTAL_NOT_READABLE'
  log 'diagnostic=CFG_METADATA_ONLY_DB_REQUIRES_PRIVILEGED_HELPER'
  log 'G10-19G3-COMPLETE=YES'
  exit 0
fi

readval(){ sed -n "s/^$1=//p" "$AMPORTAL" | head -n1; }
DBUSER="$(readval AMPDBUSER)"
DBPASS="$(readval AMPDBPASS)"
DBHOST="$(readval AMPDBHOST)"
DBHOST="${DBHOST:-localhost}"
if [ -z "$DBUSER" ] || [ -z "$DBPASS" ]; then
  log 'db_audit=BLOCKED_DB_SETTINGS_MISSING'
  log 'diagnostic=CFG_METADATA_ONLY_DB_SETTINGS_MISSING'
  log 'G10-19G3-COMPLETE=YES'
  exit 0
fi
CNF="$(mktemp "$RUNNER_TEMP/g10-19g3-db.XXXXXX.cnf")"
trap 'rm -f "$CNF"' EXIT
chmod 600 "$CNF"
escape(){ printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
{
  echo '[client]'
  printf 'user="%s"\n' "$(escape "$DBUSER")"
  printf 'password="%s"\n' "$(escape "$DBPASS")"
  printf 'host="%s"\n' "$(escape "$DBHOST")"
} > "$CNF"

ROWS="$(mysql --defaults-extra-file="$CNF" --batch --skip-column-names endpointconfig -e "SET SESSION TRANSACTION READ ONLY; SELECT CONCAT(e.mac_address,'|',COALESCE(m.name,''),'|',COALESCE(ea.account,''),'|',COALESCE(ea.priority,'')) FROM endpoint e LEFT JOIN model m ON m.id=e.id_model LEFT JOIN endpoint_account ea ON ea.id_endpoint=e.id WHERE UPPER(e.mac_address)=UPPER('$MAC') ORDER BY ea.priority; ROLLBACK;" 2>/dev/null || true)"
if [ -z "$ROWS" ]; then
  log 'endpoint_mac_found=NO'
  log 'endpoint_account_count=0'
  log 'account_202_assigned=NO'
  log 'diagnostic=ENDPOINT_ASSIGNMENT_MISSING'
else
  COUNT="$(printf '%s\n' "$ROWS" | sed '/^$/d' | wc -l | tr -d ' ')"
  log 'endpoint_mac_found=YES'
  log "endpoint_account_count=$COUNT"
  MODEL="$(printf '%s\n' "$ROWS" | head -n1 | cut -d'|' -f2)"
  log "endpoint_model=${MODEL:-UNKNOWN}"
  if printf '%s\n' "$ROWS" | awk -F'|' '$3=="202"{found=1} END{exit !found}'; then
    log 'account_202_assigned=YES'
  else
    log 'account_202_assigned=NO'
  fi
  ACCOUNTS="$(printf '%s\n' "$ROWS" | awk -F'|' '{if($3!="") print $3}' | paste -sd, -)"
  log "assigned_accounts=${ACCOUNTS:-NONE}"
  if printf '%s\n' "$ROWS" | awk -F'|' '$3=="202"{found=1} END{exit !found}' && [ -e "$CFG" ]; then
    log 'diagnostic=ASSIGNMENT_202_AND_CFG_PRESENT'
  elif [ -e "$CFG" ]; then
    log 'diagnostic=CFG_PRESENT_BUT_202_NOT_ASSIGNED'
  else
    log 'diagnostic=ASSIGNMENT_OR_CFG_INCOMPLETE'
  fi
fi
log 'G10-19G3-COMPLETE=YES'
