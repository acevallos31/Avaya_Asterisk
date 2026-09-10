#!/usr/bin/env python3
"""Add narrow Test 55 verification actions to the privileged LAB helper."""
from pathlib import Path


p = Path("deploy/j129/avaya-j129-lab-deploy")
s = p.read_text(encoding="utf-8")

funcs = r'''

verify_grandstream_test55_removal() {
  local defaults_file endpoint_count cfg_bin cfg_xml peer_201 peer_202
  defaults_file="$(make_db_defaults_file)"
  trap 'rm -f "$defaults_file"' RETURN EXIT
  endpoint_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE UPPER(REPLACE(REPLACE(REPLACE(mac_address,':',''),'-',''),'.',''))='C074ADE86609';")"
  cfg_bin='/tftpboot/cfgc074ade86609'
  cfg_xml='/tftpboot/cfgc074ade86609.xml'
  peer_201="$(asterisk -rx 'sip show peer 201' 2>/dev/null || true)"
  peer_202="$(asterisk -rx 'sip show peer 202' 2>/dev/null || true)"

  echo 'scope=TEST55_GXP1625_REMOVAL_VERIFY'
  echo 'target_mac=C0:74:AD:E8:66:09'
  echo "endpoint_rows_remaining=$endpoint_count"
  [ -e "$cfg_bin" ] && echo 'binary_cfg_absent=NO' || echo 'binary_cfg_absent=YES'
  [ -e "$cfg_xml" ] && echo 'xml_cfg_absent=NO' || echo 'xml_cfg_absent=YES'
  grep -Eq 'Name[[:space:]]*:[[:space:]]*201([[:space:]]|$)' <<<"$peer_201" && echo 'extension_201_exists=YES' || echo 'extension_201_exists=NO'
  grep -Eq 'Name[[:space:]]*:[[:space:]]*202([[:space:]]|$)' <<<"$peer_202" && echo 'extension_202_exists=YES' || echo 'extension_202_exists=NO'

  [ "$endpoint_count" -eq 0 ]
  [ ! -e "$cfg_bin" ]
  [ ! -e "$cfg_xml" ]
  grep -Eq 'Name[[:space:]]*:[[:space:]]*201([[:space:]]|$)' <<<"$peer_201"
  grep -Eq 'Name[[:space:]]*:[[:space:]]*202([[:space:]]|$)' <<<"$peer_202"
  echo 'TEST55-ENDPOINT-REMOVAL-VERIFY=PASS'
}

verify_grandstream_test55_post_reset() {
  local peer_202 phone_ip_seen
  verify_grandstream_test55_removal
  peer_202="$(asterisk -rx 'sip show peer 202' 2>/dev/null || true)"
  if grep -Fq '192.168.1.167' <<<"$peer_202"; then phone_ip_seen=YES; else phone_ip_seen=NO; fi
  echo 'scope=TEST55_GXP1625_POST_RESET_VERIFY'
  echo "extension_202_still_on_old_phone_ip=$phone_ip_seen"
  [ "$phone_ip_seen" = NO ]
  echo 'TEST55-POST-RESET-VERIFY=PASS'
}
'''

anchor = '\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor) != 1:
    raise SystemExit("Test55 action anchor missing")
if "verify_grandstream_test55_removal()" not in s:
    s = s.replace(anchor, funcs + anchor, 1)

case_anchor = "  inspect-login-patch) [ -z \"$OVERLAY_ROOT\" ] || usage; inspect_grandstream_login_patch ;;"
if case_anchor not in s:
    raise SystemExit("Test55 case anchor missing")
if "verify-grandstream-test55-removal)" not in s:
    s = s.replace(
        case_anchor,
        case_anchor
        + '\n  verify-grandstream-test55-removal) [ -z "$OVERLAY_ROOT" ] || usage; verify_grandstream_test55_removal ;;'
        + '\n  verify-grandstream-test55-post-reset) [ -z "$OVERLAY_ROOT" ] || usage; verify_grandstream_test55_post_reset ;;',
        1,
    )

p.write_text(s, encoding="utf-8")
print("TEST55-REMOVAL-VERIFIER-PREPARE=PASS")
