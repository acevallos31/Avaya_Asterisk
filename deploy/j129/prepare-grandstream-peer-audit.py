#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-call-test')
s = p.read_text()

if 'generic_peer_audit() {' in s and 'peer-audit)' in s:
    print('GRANDSTREAM-PEER-AUDIT-PREPARE-PASS')
    raise SystemExit(0)

anchor = '\ncleanup() {'
if anchor not in s:
    raise SystemExit('ERROR: no se encontro ancla cleanup')

func = r'''

generic_peer_audit() {
  local account="$REQUESTED_EXTENSION" expected_ip="$REQUESTED_IP" old_account="$PEER_EXTENSION"
  local peer ip status old_peer old_ip old_status
  [ -n "$account" ] || fail "peer-audit requires extension"
  [ -n "$expected_ip" ] || fail "peer-audit requires expected ip"

  peer="$(asterisk -rx "sip show peer $account" 2>/dev/null || true)"
  ip="$(printf '%s\n' "$peer" | sed -nE 's/^[[:space:]]*Addr->IP[[:space:]]*:[[:space:]]*([^:[:space:]]+).*/\1/p' | head -n 1)"
  if ! [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    ip="$(asterisk -rx 'sip show peers' 2>/dev/null | awk -v a="$account" '$1 ~ ("^" a "(/|$)") {print $2; exit}')"
  fi
  status="$(peer_status "$account")"

  echo 'scope=READ_ONLY_GENERIC_SIP_PEER_AUDIT'
  echo 'phone_write=NO'
  echo 'pbx_write=NO'
  echo 'sip_secret_logged=NO'
  echo "target_extension=$account"
  echo "target_ip=${ip:-UNREGISTERED}"
  echo "target_status=${status:-UNKNOWN}"

  [ "$ip" = "$expected_ip" ] || fail "target extension not registered from expected ip"
  [ "$status" = 'OK' ] || fail "target peer not ready"
  echo 'target_registration_match=YES'

  if [ -n "$old_account" ]; then
    old_peer="$(asterisk -rx "sip show peer $old_account" 2>/dev/null || true)"
    old_ip="$(printf '%s\n' "$old_peer" | sed -nE 's/^[[:space:]]*Addr->IP[[:space:]]*:[[:space:]]*([^:[:space:]]+).*/\1/p' | head -n 1)"
    if ! [[ "$old_ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
      old_ip="$(asterisk -rx 'sip show peers' 2>/dev/null | awk -v a="$old_account" '$1 ~ ("^" a "(/|$)") {print $2; exit}')"
    fi
    old_status="$(peer_status "$old_account")"
    echo "previous_extension=$old_account"
    echo "previous_ip=${old_ip:-UNREGISTERED}"
    echo "previous_status=${old_status:-UNKNOWN}"
    if [ "$old_ip" = "$expected_ip" ]; then
      echo 'previous_extension_still_on_phone_ip=YES'
      fail "previous extension still registered from target phone ip"
    else
      echo 'previous_extension_still_on_phone_ip=NO'
    fi
  fi

  echo 'GENERIC-SIP-PEER-AUDIT-PASS'
}
'''

s = s.replace(anchor, func + anchor, 1)
case_anchor = '  cleanup)\n    cleanup\n    ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: no se encontro ancla del case cleanup')
s = s.replace(case_anchor, '  peer-audit)\n    generic_peer_audit\n    ;;\n' + case_anchor, 1)
p.write_text(s)
print('GRANDSTREAM-PEER-AUDIT-PREPARE-PASS')
