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
  rm -f "$defaults_file"
  trap - RETURN EXIT
  echo 'TEST55-ENDPOINT-REMOVAL-VERIFY=PASS'
}

verify_grandstream_test55_post_reset() {
  local peer_202 phone_ip_seen
  verify_grandstream_test55_removal
  peer_202="$(asterisk -rx 'sip show peer 202' 2>/dev/null || true)"
  if grep -Fq '192.168.1.168' <<<"$peer_202"; then phone_ip_seen=YES; else phone_ip_seen=NO; fi
  echo 'scope=TEST55_GXP1625_POST_RESET_VERIFY'
  echo "extension_202_still_on_old_phone_ip=$phone_ip_seen"
  [ "$phone_ip_seen" = NO ]
  echo 'TEST55-POST-RESET-VERIFY=PASS'
}

inspect_grandstream_test55_rediscovered() {
  local defaults_file endpoint_count endpoint_id endpoint_ip manufacturer model
  local selected account_count override_count cfg_bin cfg_xml peer_201 peer_202
  local peer_202_target_ip peer_202_status phone_http_status
  defaults_file="$(make_db_defaults_file)"
  trap 'rm -f "$defaults_file"' RETURN EXIT
  endpoint_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE UPPER(REPLACE(REPLACE(REPLACE(mac_address,':',''),'-',''),'.',''))='C074ADE86609';")"

  endpoint_id=''
  endpoint_ip=''
  manufacturer=''
  model=''
  selected=''
  account_count=''
  override_count=''
  if [ "$endpoint_count" -eq 1 ]; then
    endpoint_id="$(mysql_scalar "$defaults_file" "SELECT id FROM endpoint WHERE UPPER(REPLACE(REPLACE(REPLACE(mac_address,':',''),'-',''),'.',''))='C074ADE86609' LIMIT 1;")"
    endpoint_ip="$(mysql_scalar "$defaults_file" "SELECT last_known_ipv4 FROM endpoint WHERE id=${endpoint_id};")"
    manufacturer="$(mysql_scalar "$defaults_file" "SELECT mf.name FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer WHERE e.id=${endpoint_id};")"
    model="$(mysql_scalar "$defaults_file" "SELECT COALESCE(m.name,'') FROM endpoint e LEFT JOIN model m ON m.id=e.id_model WHERE e.id=${endpoint_id};")"
    selected="$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${endpoint_id};")"
    account_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_account WHERE id_endpoint=${endpoint_id};")"
    override_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_properties WHERE id_endpoint=${endpoint_id} AND property_key='http_password';")"
  fi

  cfg_bin='/tftpboot/cfgc074ade86609'
  cfg_xml='/tftpboot/cfgc074ade86609.xml'
  peer_201="$(asterisk -rx 'sip show peer 201' 2>/dev/null || true)"
  peer_202="$(asterisk -rx 'sip show peer 202' 2>/dev/null || true)"
  if grep -Fq '192.168.1.168' <<<"$peer_202"; then peer_202_target_ip=YES; else peer_202_target_ip=NO; fi
  if grep -Eq 'Status[[:space:]]*:[[:space:]]*OK' <<<"$peer_202"; then
    peer_202_status=OK
  elif grep -Eq 'Status[[:space:]]*:[[:space:]]*UNREACHABLE' <<<"$peer_202"; then
    peer_202_status=UNREACHABLE
  else
    peer_202_status=UNKNOWN
  fi
  phone_http_status="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 http://192.168.1.168/ || true)"

  echo 'scope=TEST55_GXP1625_POST_RESET_AUDIT'
  echo 'target_mac=C0:74:AD:E8:66:09'
  echo "endpoint_rows=$endpoint_count"
  echo "endpoint_ip=${endpoint_ip:-NONE}"
  echo "manufacturer=${manufacturer:-NONE}"
  echo "model=${model:-NONE}"
  echo "selected=${selected:-NONE}"
  echo "account_count=${account_count:-NONE}"
  echo "http_password_override_count=${override_count:-NONE}"
  [ -e "$cfg_bin" ] && echo 'binary_cfg_absent=NO' || echo 'binary_cfg_absent=YES'
  [ -e "$cfg_xml" ] && echo 'xml_cfg_absent=NO' || echo 'xml_cfg_absent=YES'
  grep -Eq 'Name[[:space:]]*:[[:space:]]*201([[:space:]]|$)' <<<"$peer_201" && echo 'extension_201_exists=YES' || echo 'extension_201_exists=NO'
  grep -Eq 'Name[[:space:]]*:[[:space:]]*202([[:space:]]|$)' <<<"$peer_202" && echo 'extension_202_exists=YES' || echo 'extension_202_exists=NO'
  echo "extension_202_registered_at_target_ip=$peer_202_target_ip"
  echo "extension_202_status=$peer_202_status"
  echo "phone_http_status=${phone_http_status:-000}"

  [ "$endpoint_count" -eq 1 ]
  [ "$endpoint_ip" = '192.168.1.168' ]
  [ "$manufacturer" = 'Grandstream' ]
  [ "$model" = 'GXP1625' ]
  [ "$selected" -eq 0 ]
  [ "$account_count" -eq 0 ]
  [ "$override_count" -eq 0 ]
  [ ! -e "$cfg_bin" ]
  [ ! -e "$cfg_xml" ]
  grep -Eq 'Name[[:space:]]*:[[:space:]]*201([[:space:]]|$)' <<<"$peer_201"
  grep -Eq 'Name[[:space:]]*:[[:space:]]*202([[:space:]]|$)' <<<"$peer_202"
  [ "$phone_http_status" = 200 ]
  rm -f "$defaults_file"
  trap - RETURN EXIT
  echo 'TEST55-POST-RESET-AUDIT=PASS'
}

inspect_grandstream_test55_configured() {
  local d n id ip mf md sel ac a202 bin xml peers p202 p201 http
  d="$(make_db_defaults_file)"; trap 'rm -f "$d"' RETURN EXIT
  n="$(mysql_scalar "$d" "SELECT COUNT(*) FROM endpoint WHERE UPPER(REPLACE(REPLACE(REPLACE(mac_address,':',''),'-',''),'.',''))='C074ADE86609';")"
  id=''; ip=''; mf=''; md=''; sel=''; ac=''; a202=''
  if [ "$n" -eq 1 ]; then
    id="$(mysql_scalar "$d" "SELECT id FROM endpoint WHERE UPPER(REPLACE(REPLACE(REPLACE(mac_address,':',''),'-',''),'.',''))='C074ADE86609' LIMIT 1;")"
    ip="$(mysql_scalar "$d" "SELECT last_known_ipv4 FROM endpoint WHERE id=$id;")"
    mf="$(mysql_scalar "$d" "SELECT mf.name FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer WHERE e.id=$id;")"
    md="$(mysql_scalar "$d" "SELECT COALESCE(m.name,'') FROM endpoint e LEFT JOIN model m ON m.id=e.id_model WHERE e.id=$id;")"
    sel="$(mysql_scalar "$d" "SELECT selected FROM endpoint WHERE id=$id;")"
    ac="$(mysql_scalar "$d" "SELECT COUNT(*) FROM endpoint_account WHERE id_endpoint=$id;")"
    a202="$(mysql_scalar "$d" "SELECT COUNT(*) FROM endpoint_account WHERE id_endpoint=$id AND tech='sip' AND account='202';")"
  fi
  bin='/tftpboot/cfgc074ade86609'; xml='/tftpboot/cfgc074ade86609.xml'
  peers="$(asterisk -rx 'sip show peers' 2>/dev/null || true)"
  p202="$(printf '%s\n' "$peers" | awk '$1 ~ /^202(\/|$)/ {print $2; exit}')"
  p201="$(printf '%s\n' "$peers" | awk '$1 ~ /^201(\/|$)/ {print $2; exit}')"
  http="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 http://192.168.1.168/ || true)"
  echo 'scope=TEST55_GXP1625_POST_CONFIG_AUDIT'; echo 'target_mac=C0:74:AD:E8:66:09'
  echo "endpoint_rows=$n"; echo "endpoint_ip=${ip:-NONE}"; echo "manufacturer=${mf:-NONE}"; echo "model=${md:-NONE}"
  echo "selected=${sel:-NONE}"; echo "account_count=${ac:-NONE}"; echo "target_account_202_sip_count=${a202:-NONE}"
  [ -s "$bin" ] && echo 'binary_cfg_present=YES' || echo 'binary_cfg_present=NO'
  [ -s "$xml" ] && echo 'xml_cfg_present=YES' || echo 'xml_cfg_present=NO'
  if [ -s "$xml" ]; then
    python3 - "$xml" <<'PY'
import sys, xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot(); c=r.find('config'); v={x.tag:(x.text or '') for x in c} if c is not None else {}
print('xml_root_valid=' + ('YES' if r.tag=='gs_provision' else 'NO'))
print('xml_mac_binding=' + ('YES' if (r.findtext('mac') or '').lower()=='c074ade86609' else 'NO'))
print('xml_p35_target_202=' + ('YES' if v.get('P35')=='202' else 'NO'))
print('xml_p36_target_202=' + ('YES' if v.get('P36')=='202' else 'NO'))
print('xml_p34_secret_present=' + ('YES' if bool(v.get('P34')) else 'NO'))
print('xml_p47_target_pbx=' + ('YES' if v.get('P47')=='192.168.1.10' else 'NO'))
print('xml_p270_target_ashly=' + ('YES' if 'ashly' in v.get('P270','').lower() else 'NO'))
PY
  fi
  echo "target_ip=${p202:-UNREGISTERED}"; echo "previous_ip=${p201:-UNREGISTERED}"; echo "phone_http_status=${http:-000}"
  [ "$p202" = '192.168.1.168' ] && echo 'target_registration_match=YES' || echo 'target_registration_match=NO'
  [ "$p201" = '192.168.1.168' ] && echo 'previous_extension_still_on_phone_ip=YES' || echo 'previous_extension_still_on_phone_ip=NO'
  [ "$n" -eq 1 ]; [ "$ip" = '192.168.1.168' ]; [ "$mf" = 'Grandstream' ]; [ "$md" = 'GXP1625' ]
  [ "$sel" -eq 0 ]; [ "$ac" -eq 1 ]; [ "$a202" -eq 1 ]; [ -s "$bin" ]; [ -s "$xml" ]; [ "$http" = 200 ]
  python3 - "$xml" <<'PY'
import sys, xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot(); c=r.find('config'); assert r.tag=='gs_provision' and c is not None
v={x.tag:(x.text or '') for x in c}; assert (r.findtext('mac') or '').lower()=='c074ade86609'
assert v.get('P35')=='202' and v.get('P36')=='202' and bool(v.get('P34'))
assert v.get('P47')=='192.168.1.10' and 'ashly' in v.get('P270','').lower()
PY
  [ "$p202" = '192.168.1.168' ]; [ "$p201" != '192.168.1.168' ]
  rm -f "$d"; trap - RETURN EXIT; echo 'TEST55-POST-CONFIG-AUDIT=PASS'
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
        + '\n  verify-grandstream-test55-post-reset) [ -z "$OVERLAY_ROOT" ] || usage; verify_grandstream_test55_post_reset ;;'
        + '\n  inspect-grandstream-test55-rediscovered) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_test55_rediscovered ;;'
        + '\n  inspect-grandstream-test55-configured) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_test55_configured ;;',
        1,
    )

p.write_text(s, encoding="utf-8")
print("TEST55-REMOVAL-VERIFIER-PREPARE=PASS")
