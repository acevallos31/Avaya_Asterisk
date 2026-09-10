#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'run_grandstream_202_registration_inspection()' not in s:
    marker = '\n[ -n "$ACTION" ] || usage\n'
    if marker not in s:
        raise SystemExit('helper insertion marker not found')
    fn = r'''

run_grandstream_202_registration_inspection() {
  local account='202' phone_ip='192.168.1.167' sip_out pjsip_out
  command -v asterisk >/dev/null 2>&1 || { echo 'ERROR: asterisk CLI no disponible' >&2; exit 1; }
  echo '=== GXP1625 SIP REGISTRATION AUDIT (SOLO LECTURA) ==='
  echo "account=$account"
  echo "expected_phone_ip=$phone_ip"
  echo 'sip_secret_logged=NO'
  sip_out="$(asterisk -rx 'sip show peers' 2>/dev/null || true)"
  pjsip_out="$(asterisk -rx 'pjsip show contacts' 2>/dev/null || true)"
  if printf '%s\n' "$sip_out" | grep -E "(^|[[:space:]])${account}(/|[[:space:]])" | grep -F "$phone_ip" >/dev/null 2>&1; then
    echo 'chan_sip_account_ip_match=YES'
  else
    echo 'chan_sip_account_ip_match=NO'
  fi
  if printf '%s\n' "$pjsip_out" | grep -F "$account" | grep -F "$phone_ip" >/dev/null 2>&1; then
    echo 'pjsip_account_ip_match=YES'
  else
    echo 'pjsip_account_ip_match=NO'
  fi
  if printf '%s\n' "$sip_out" | grep -E "(^|[[:space:]])${account}(/|[[:space:]])" >/dev/null 2>&1; then
    echo 'chan_sip_account_present=YES'
  else
    echo 'chan_sip_account_present=NO'
  fi
  echo 'GRANDSTREAM-202-REGISTRATION-AUDIT-PASS'
}
'''
    s = s.replace(marker, fn + marker, 1)

old = "  inspect-sip-registration) [ -z \"$OVERLAY_ROOT\" ] || usage; run_sip_registration_inspection ;;\n"
new = old + "  inspect-grandstream-202-registration) [ -z \"$OVERLAY_ROOT\" ] || usage; run_grandstream_202_registration_inspection ;;\n"
if 'inspect-grandstream-202-registration)' not in s:
    if old not in s:
        raise SystemExit('case insertion marker not found')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
