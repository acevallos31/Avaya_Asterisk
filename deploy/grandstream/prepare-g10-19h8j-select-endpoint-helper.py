#!/usr/bin/env python3
"""Prepare reversible selection of the exact GXP1625/202 endpoint.

Endpoint Configurator clears endpoint.selected after applyconfig. This helper
recreates the GUI selection step for automated lab validation while refusing to
select anything if another endpoint is already selected. State contains only
endpoint id and previous selected flag.
"""
from pathlib import Path

p=Path('deploy/j129/avaya-j129-lab-deploy')
s=p.read_text(encoding='utf-8')
marker='# G10-19H8J-SELECT-ENDPOINT'
if marker in s:
    print('G10-19H8J-SELECT-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

if 'GRANDSTREAM_H8J_SELECT_STATE=' not in s:
    anchor='GRANDSTREAM_OUI_STATE_FILE="$STATE_DIR/grandstream-c074ad.state"\n'
    if s.count(anchor)!=1:
        raise SystemExit('H8J select state anchor missing')
    s=s.replace(anchor,anchor+'GRANDSTREAM_H8J_SELECT_STATE="$STATE_DIR/grandstream-gxp1625-select.state"\n',1)

anchor='\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor)!=1:
    raise SystemExit('H8J select action anchor missing')

funcs=r'''

# G10-19H8J-SELECT-ENDPOINT
select_grandstream_gxp1625_202() {
  [ ! -e "$GRANDSTREAM_H8J_SELECT_STATE" ] || { echo 'ERROR: H8J selection state already exists' >&2; exit 1; }
  local defaults_file endpoint_count endpoint_id account_count other_selected previous
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  endpoint_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Grandstream' AND m.name='GXP1625' AND e.mac_address='C0:74:AD:E8:66:09' AND e.last_known_ipv4='192.168.1.167';")"
  [ "$endpoint_count" -eq 1 ] || { echo "ERROR: exact target endpoint count=$endpoint_count" >&2; exit 1; }
  endpoint_id="$(mysql_scalar "$defaults_file" "SELECT e.id FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Grandstream' AND m.name='GXP1625' AND e.mac_address='C0:74:AD:E8:66:09' AND e.last_known_ipv4='192.168.1.167' LIMIT 1;")"
  [[ "$endpoint_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: invalid target endpoint id' >&2; exit 1; }
  account_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_account WHERE id_endpoint=${endpoint_id} AND tech='sip' AND account='202';")"
  [ "$account_count" -eq 1 ] || { echo "ERROR: target account 202 association count=$account_count" >&2; exit 1; }
  other_selected="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE selected=1 AND id<>${endpoint_id};")"
  [ "$other_selected" -eq 0 ] || { echo "ERROR: another endpoint is selected count=$other_selected" >&2; exit 1; }
  previous="$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${endpoint_id};")"
  [[ "$previous" =~ ^[01]$ ]] || { echo 'ERROR: invalid previous selected state' >&2; exit 1; }
  install -d -o root -g root -m 0700 "$STATE_DIR"
  {
    printf 'endpoint_id=%s\n' "$endpoint_id"
    printf 'previous=%s\n' "$previous"
  } > "$GRANDSTREAM_H8J_SELECT_STATE"
  chmod 0600 "$GRANDSTREAM_H8J_SELECT_STATE"
  mysql --defaults-extra-file="$defaults_file" endpointconfig -e "UPDATE endpoint SET selected=1 WHERE id=${endpoint_id};"
  [ "$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${endpoint_id};")" -eq 1 ] || { echo 'ERROR: target selection did not persist' >&2; exit 1; }
  rm -f "$defaults_file"; trap - RETURN EXIT
  echo 'scope=CONTROLLED_EXACT_ENDPOINT_SELECTION'
  echo 'db_write=YES_SELECTED_FLAG_ONLY'
  echo 'target_mac=C0:74:AD:E8:66:09'
  echo 'target_account=202'
  echo "previous_selected=$previous"
  echo 'selected_now=YES'
  echo 'G10-19H8J-SELECT-ENDPOINT-PASS'
}

rollback_grandstream_gxp1625_selection() {
  [ -f "$GRANDSTREAM_H8J_SELECT_STATE" ] || { echo 'G10-19H8J-SELECT-ROLLBACK=ALREADY_CLEAN'; return 0; }
  local endpoint_id previous defaults_file
  endpoint_id="$(sed -n 's/^endpoint_id=//p' "$GRANDSTREAM_H8J_SELECT_STATE")"
  previous="$(sed -n 's/^previous=//p' "$GRANDSTREAM_H8J_SELECT_STATE")"
  [[ "$endpoint_id" =~ ^[0-9]+$ && "$previous" =~ ^[01]$ ]] || { echo 'ERROR: invalid H8J selection state' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  mysql --defaults-extra-file="$defaults_file" endpointconfig -e "UPDATE endpoint SET selected=${previous} WHERE id=${endpoint_id};"
  [ "$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${endpoint_id};")" -eq "$previous" ] || { echo 'ERROR: selection rollback verification failed' >&2; exit 1; }
  rm -f "$GRANDSTREAM_H8J_SELECT_STATE" "$defaults_file"; trap - RETURN EXIT
  echo "selected_restored_to=$previous"
  echo 'G10-19H8J-SELECT-ROLLBACK-PASS'
}

commit_grandstream_gxp1625_selection() {
  [ -f "$GRANDSTREAM_H8J_SELECT_STATE" ] || { echo 'ERROR: H8J selection state missing' >&2; exit 1; }
  local endpoint_id defaults_file current
  endpoint_id="$(sed -n 's/^endpoint_id=//p' "$GRANDSTREAM_H8J_SELECT_STATE")"
  [[ "$endpoint_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: invalid selection endpoint id' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  current="$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${endpoint_id};")"
  [ "$current" -eq 0 ] || { echo "ERROR: Endpoint Configurator did not clear selected flag current=$current" >&2; exit 1; }
  rm -f "$GRANDSTREAM_H8J_SELECT_STATE" "$defaults_file"; trap - RETURN EXIT
  echo 'selected_after_applyconfig=0'
  echo 'G10-19H8J-SELECT-COMMIT-PASS'
}
'''

s=s.replace(anchor,funcs+anchor,1)
case_anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8J select case anchor missing')
s=s.replace(case_anchor,case_anchor
    +'\n  select-grandstream-gxp1625-202) [ -z "$OVERLAY_ROOT" ] || usage; select_grandstream_gxp1625_202 ;;'
    +'\n  rollback-grandstream-gxp1625-selection) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_gxp1625_selection ;;'
    +'\n  commit-grandstream-gxp1625-selection) [ -z "$OVERLAY_ROOT" ] || usage; commit_grandstream_gxp1625_selection ;;',1)
p.write_text(s,encoding='utf-8')
print('G10-19H8J-SELECT-HELPER-PREPARE=PASS')
