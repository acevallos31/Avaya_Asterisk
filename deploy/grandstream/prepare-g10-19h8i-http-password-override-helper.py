#!/usr/bin/env python3
"""Prepare reversible endpoint-specific Grandstream HTTP password override actions.

The password is read from stdin, never printed, never placed in argv, and never
stored in the helper state file. If no override exists, one row is inserted for
the exact GXP1625 endpoint. If an identical override already exists, it is reused.
A state file records only whether the row was created by this test so rollback
can remove only what this test created.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H8I-HTTP-PASSWORD-OVERRIDE'
if marker in s:
    print('G10-19H8I-DB-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

if 'GRANDSTREAM_HTTP_OVERRIDE_STATE=' not in s:
    anchor = 'GRANDSTREAM_OUI_STATE_FILE="$STATE_DIR/grandstream-c074ad.state"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8I DB state anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_HTTP_OVERRIDE_STATE="$STATE_DIR/grandstream-gxp1625-http-password.state"\n', 1)

anchor = '\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor) != 1:
    raise SystemExit('H8I DB helper action anchor missing')

funcs = r'''

# G10-19H8I-HTTP-PASSWORD-OVERRIDE
apply_grandstream_http_password_override() {
  local supplied secret_hex defaults_file endpoint_count endpoint_id override_count current_hex property_id mode
  IFS= read -r supplied
  [ -n "$supplied" ] || { echo 'ERROR: phone password missing on stdin' >&2; exit 1; }
  secret_hex="$(printf '%s' "$supplied" | od -An -tx1 | tr -d ' \n')"
  [ -n "$secret_hex" ] || { echo 'ERROR: password encoding failed' >&2; exit 1; }
  install -d -o root -g root -m 0700 "$STATE_DIR"
  [ ! -e "$GRANDSTREAM_HTTP_OVERRIDE_STATE" ] || { echo 'ERROR: H8I override state already exists' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT

  endpoint_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Grandstream' AND m.name='GXP1625' AND e.mac_address='C0:74:AD:E8:66:09' AND e.last_known_ipv4='192.168.1.167';")"
  [ "$endpoint_count" -eq 1 ] || { echo "ERROR: exact GXP1625 endpoint count=$endpoint_count" >&2; exit 1; }
  endpoint_id="$(mysql_scalar "$defaults_file" "SELECT e.id FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Grandstream' AND m.name='GXP1625' AND e.mac_address='C0:74:AD:E8:66:09' AND e.last_known_ipv4='192.168.1.167' LIMIT 1;")"
  [[ "$endpoint_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: invalid endpoint id' >&2; exit 1; }
  override_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_properties WHERE id_endpoint=${endpoint_id} AND property_key='http_password';")"

  mode=''
  property_id=''
  if [ "$override_count" -eq 0 ]; then
    mysql --defaults-extra-file="$defaults_file" --batch --skip-column-names endpointconfig -e "INSERT INTO endpoint_properties (id_endpoint,property_key,property_value) VALUES (${endpoint_id},'http_password',UNHEX('${secret_hex}'));"
    property_id="$(mysql_scalar "$defaults_file" "SELECT id FROM endpoint_properties WHERE id_endpoint=${endpoint_id} AND property_key='http_password' ORDER BY id DESC LIMIT 1;")"
    [[ "$property_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: inserted property id invalid' >&2; exit 1; }
    current_hex="$(mysql_scalar "$defaults_file" "SELECT LOWER(HEX(property_value)) FROM endpoint_properties WHERE id=${property_id} AND id_endpoint=${endpoint_id} AND property_key='http_password';")"
    if [ "$current_hex" != "$secret_hex" ]; then
      mysql --defaults-extra-file="$defaults_file" endpointconfig -e "DELETE FROM endpoint_properties WHERE id=${property_id} AND id_endpoint=${endpoint_id} AND property_key='http_password';"
      echo 'ERROR: inserted override verification failed; row removed' >&2
      exit 1
    fi
    mode='CREATED'
  elif [ "$override_count" -eq 1 ]; then
    property_id="$(mysql_scalar "$defaults_file" "SELECT id FROM endpoint_properties WHERE id_endpoint=${endpoint_id} AND property_key='http_password' LIMIT 1;")"
    current_hex="$(mysql_scalar "$defaults_file" "SELECT LOWER(HEX(property_value)) FROM endpoint_properties WHERE id=${property_id};")"
    [ "$current_hex" = "$secret_hex" ] || { echo 'ERROR: an existing endpoint override differs from the supplied lab secret; refusing overwrite' >&2; exit 1; }
    mode='EXISTING'
  else
    echo "ERROR: duplicate http_password endpoint overrides count=$override_count" >&2
    exit 1
  fi

  {
    printf 'mode=%s\n' "$mode"
    printf 'endpoint_id=%s\n' "$endpoint_id"
    printf 'property_id=%s\n' "$property_id"
  } > "$GRANDSTREAM_HTTP_OVERRIDE_STATE"
  chmod 0600 "$GRANDSTREAM_HTTP_OVERRIDE_STATE"
  supplied=''; secret_hex=''; current_hex=''
  rm -f "$defaults_file"; trap - RETURN EXIT

  echo 'scope=CONTROLLED_ENDPOINT_HTTP_PASSWORD_OVERRIDE'
  echo 'secret_values_logged=NO'
  echo 'target_mac=C0:74:AD:E8:66:09'
  echo 'target_model=GXP1625'
  echo "override_mode=$mode"
  echo 'effective_http_password_matches_supplied=YES'
  echo 'G10-19H8I-HTTP-PASSWORD-OVERRIDE-APPLY-PASS'
}

rollback_grandstream_http_password_override() {
  [ -f "$GRANDSTREAM_HTTP_OVERRIDE_STATE" ] || { echo 'G10-19H8I-HTTP-PASSWORD-OVERRIDE-ROLLBACK=ALREADY_CLEAN'; return 0; }
  local mode endpoint_id property_id defaults_file remaining
  mode="$(sed -n 's/^mode=//p' "$GRANDSTREAM_HTTP_OVERRIDE_STATE")"
  endpoint_id="$(sed -n 's/^endpoint_id=//p' "$GRANDSTREAM_HTTP_OVERRIDE_STATE")"
  property_id="$(sed -n 's/^property_id=//p' "$GRANDSTREAM_HTTP_OVERRIDE_STATE")"
  [[ "$endpoint_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: invalid rollback endpoint id' >&2; exit 1; }
  [[ "$property_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: invalid rollback property id' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  if [ "$mode" = 'CREATED' ]; then
    mysql --defaults-extra-file="$defaults_file" endpointconfig -e "DELETE FROM endpoint_properties WHERE id=${property_id} AND id_endpoint=${endpoint_id} AND property_key='http_password';"
    remaining="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_properties WHERE id=${property_id};")"
    [ "$remaining" -eq 0 ] || { echo 'ERROR: created override row still exists after rollback' >&2; exit 1; }
    echo 'db_row_removed=YES'
  elif [ "$mode" = 'EXISTING' ]; then
    echo 'db_row_removed=NO_EXISTING_ROW_PRESERVED'
  else
    echo 'ERROR: unknown H8I override state mode' >&2; exit 1
  fi
  rm -f "$GRANDSTREAM_HTTP_OVERRIDE_STATE" "$defaults_file"; trap - RETURN EXIT
  echo 'secret_values_logged=NO'
  echo 'G10-19H8I-HTTP-PASSWORD-OVERRIDE-ROLLBACK-PASS'
}

commit_grandstream_http_password_override() {
  [ -f "$GRANDSTREAM_HTTP_OVERRIDE_STATE" ] || { echo 'ERROR: no H8I override state to commit' >&2; exit 1; }
  local endpoint_id property_id defaults_file count
  endpoint_id="$(sed -n 's/^endpoint_id=//p' "$GRANDSTREAM_HTTP_OVERRIDE_STATE")"
  property_id="$(sed -n 's/^property_id=//p' "$GRANDSTREAM_HTTP_OVERRIDE_STATE")"
  [[ "$endpoint_id" =~ ^[0-9]+$ && "$property_id" =~ ^[0-9]+$ ]] || { echo 'ERROR: invalid H8I state' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_properties WHERE id=${property_id} AND id_endpoint=${endpoint_id} AND property_key='http_password';")"
  [ "$count" -eq 1 ] || { echo 'ERROR: override row missing at commit' >&2; exit 1; }
  rm -f "$GRANDSTREAM_HTTP_OVERRIDE_STATE" "$defaults_file"; trap - RETURN EXIT
  echo 'db_override_retained=YES'
  echo 'secret_values_logged=NO'
  echo 'G10-19H8I-HTTP-PASSWORD-OVERRIDE-COMMIT-PASS'
}
'''

s = s.replace(anchor, funcs + anchor, 1)
case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8I DB helper case anchor missing')
s = s.replace(case_anchor, case_anchor
    + '\n  apply-grandstream-http-password-override) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_http_password_override ;;'
    + '\n  rollback-grandstream-http-password-override) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_http_password_override ;;'
    + '\n  commit-grandstream-http-password-override) [ -z "$OVERLAY_ROOT" ] || usage; commit_grandstream_http_password_override ;;', 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8I-DB-HELPER-PREPARE=PASS')
