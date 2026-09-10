#!/usr/bin/env python3
from pathlib import Path

p=Path('deploy/j129/avaya-j129-lab-deploy')
s=p.read_text()
if 'run_endpointconfig_selected_audit() {' in s and 'inspect-endpointconfig-selected)' in s:
    print('ENDPOINTCONFIG-SELECTED-AUDIT-PREPARE=PASS')
    raise SystemExit(0)
anchor='\ninstall_db_j129() {'
if anchor not in s:
    raise SystemExit('ERROR: install_db_j129 anchor missing')
func=r'''

run_endpointconfig_selected_audit() {
  local defaults_file
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  echo 'scope=READ_ONLY_ENDPOINTCONFIG_SELECTED_AUDIT'
  echo 'phone_write=NO'
  echo 'pbx_write=NO'
  echo 'db_write=NO'
  echo 'sip_secret_logged=NO'
  echo '=== SELECTED ENDPOINTS ==='
  mysql --defaults-extra-file="$defaults_file" --batch --raw endpointconfig <<'SQL'
SET SESSION TRANSACTION READ ONLY;
SELECT e.id, mf.name AS manufacturer, COALESCE(m.name,'') AS model, e.mac_address, e.last_known_ipv4, e.selected,
       COALESCE(GROUP_CONCAT(ea.account ORDER BY ea.priority SEPARATOR ','),'') AS accounts
FROM endpoint e
JOIN manufacturer mf ON mf.id=e.id_manufacturer
LEFT JOIN model m ON m.id=e.id_model
LEFT JOIN endpoint_account ea ON ea.id_endpoint=e.id
WHERE e.selected=1
GROUP BY e.id,mf.name,m.name,e.mac_address,e.last_known_ipv4,e.selected
ORDER BY e.id;
SELECT CONCAT('selected_count=',COUNT(*)) FROM endpoint WHERE selected=1;
SELECT CONCAT('target_gxp1625_selected_count=',COUNT(*))
FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer LEFT JOIN model m ON m.id=e.id_model
WHERE e.selected=1 AND mf.name='Grandstream' AND m.name='GXP1625' AND e.mac_address='C0:74:AD:E8:66:09' AND e.last_known_ipv4='192.168.1.167';
ROLLBACK;
SQL
  rm -f "$defaults_file"; trap - RETURN EXIT
  echo 'ENDPOINTCONFIG-SELECTED-AUDIT-PASS'
}
'''
s=s.replace(anchor,func+anchor,1)
case_anchor='  inspect-sip-registration) [ -z "$OVERLAY_ROOT" ] || usage; run_sip_registration_inspection ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: inspect-sip-registration case anchor missing')
s=s.replace(case_anchor,case_anchor+'\n  inspect-endpointconfig-selected) [ -z "$OVERLAY_ROOT" ] || usage; run_endpointconfig_selected_audit ;;',1)
p.write_text(s)
print('ENDPOINTCONFIG-SELECTED-AUDIT-PREPARE=PASS')
