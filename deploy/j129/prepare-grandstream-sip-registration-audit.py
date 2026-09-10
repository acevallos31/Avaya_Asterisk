#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text()

if 'run_grandstream_sip_registration_inspection() {' in s and 'inspect-grandstream-sip-registration)' in s:
    print('GRANDSTREAM-SIP-REGISTRATION-PREPARE-PASS')
    raise SystemExit(0)

anchor = '\ninstall_db_j129() {'
if anchor not in s:
    raise SystemExit('ERROR: no se encontro ancla install_db_j129')

func = r'''

run_grandstream_sip_registration_inspection() {
  local target='202' previous='201' expected_ip='192.168.1.167'
  local sip_out pjsip_out target_ip='' target_status='' previous_ip='' previous_status=''
  command -v asterisk >/dev/null 2>&1 || { echo 'ERROR: asterisk CLI no disponible' >&2; exit 1; }

  echo 'scope=READ_ONLY_GRANDSTREAM_SIP_REGISTRATION_AUDIT'
  echo 'phone_write=NO'
  echo 'pbx_write=NO'
  echo 'sip_secret_logged=NO'

  sip_out="$(asterisk -rx 'sip show peers' 2>/dev/null || true)"
  pjsip_out="$(asterisk -rx 'pjsip show contacts' 2>/dev/null || true)"

  target_ip="$(printf '%s\n' "$sip_out" | awk -v a="$target" '$1 ~ ("^" a "(/|$)") {print $2; exit}')"
  target_status="$(printf '%s\n' "$sip_out" | awk -v a="$target" '$1 ~ ("^" a "(/|$)") {for(i=1;i<=NF;i++) if($i ~ /^(OK|UNKNOWN|UNREACHABLE)$/){print $i; exit}}')"
  if [ -z "$target_ip" ] && printf '%s\n' "$pjsip_out" | grep -F "$target" | grep -F "$expected_ip" >/dev/null 2>&1; then
    target_ip="$expected_ip"
    target_status='OK'
  fi

  previous_ip="$(printf '%s\n' "$sip_out" | awk -v a="$previous" '$1 ~ ("^" a "(/|$)") {print $2; exit}')"
  previous_status="$(printf '%s\n' "$sip_out" | awk -v a="$previous" '$1 ~ ("^" a "(/|$)") {for(i=1;i<=NF;i++) if($i ~ /^(OK|UNKNOWN|UNREACHABLE)$/){print $i; exit}}')"
  if [ -z "$previous_ip" ] && printf '%s\n' "$pjsip_out" | grep -F "$previous" | grep -F "$expected_ip" >/dev/null 2>&1; then
    previous_ip="$expected_ip"
    previous_status='OK'
  fi

  echo "target_extension=$target"
  echo "target_ip=${target_ip:-UNREGISTERED}"
  echo "target_status=${target_status:-UNKNOWN}"
  if [ "$target_ip" = "$expected_ip" ]; then
    echo 'target_registration_match=YES'
  else
    echo 'target_registration_match=NO'
  fi

  echo "previous_extension=$previous"
  echo "previous_ip=${previous_ip:-UNREGISTERED}"
  echo "previous_status=${previous_status:-UNKNOWN}"
  if [ "$previous_ip" = "$expected_ip" ]; then
    echo 'previous_extension_still_on_phone_ip=YES'
  else
    echo 'previous_extension_still_on_phone_ip=NO'
  fi

  [ "$target_ip" = "$expected_ip" ] || { echo 'GRANDSTREAM-SIP-REGISTRATION-FAIL'; exit 1; }
  [ "$previous_ip" != "$expected_ip" ] || { echo 'GRANDSTREAM-SIP-REGISTRATION-FAIL'; exit 1; }
  echo 'GRANDSTREAM-SIP-REGISTRATION-PASS'
}
'''

s = s.replace(anchor, func + anchor, 1)
case_anchor = '  inspect-sip-registration) [ -z "$OVERLAY_ROOT" ] || usage; run_sip_registration_inspection ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: no se encontro ancla inspect-sip-registration')
s = s.replace(case_anchor, case_anchor + '\n  inspect-grandstream-sip-registration) [ -z "$OVERLAY_ROOT" ] || usage; run_grandstream_sip_registration_inspection ;;', 1)
p.write_text(s)
print('GRANDSTREAM-SIP-REGISTRATION-PREPARE-PASS')
