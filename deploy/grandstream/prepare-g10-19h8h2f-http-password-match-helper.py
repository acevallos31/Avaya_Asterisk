#!/usr/bin/env python3
"""Prepare a restricted read-only comparison of Issabel's effective HTTP password.

The candidate phone password is read from stdin and is never printed or placed
in argv. The helper reports only whether it matches the effective Endpoint
Configurator property and whether that property comes from an endpoint override
or the model default.
"""
from pathlib import Path

p=Path('deploy/j129/avaya-j129-lab-deploy')
s=p.read_text(encoding='utf-8')
marker='# G10-19H8H2F-HTTP-PASSWORD-MATCH'
if marker in s:
    print('G10-19H8H2F-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)
anchor='\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor)!=1:
    raise SystemExit('H8H2F helper action anchor missing')
func=r'''

# G10-19H8H2F-HTTP-PASSWORD-MATCH
compare_grandstream_http_password() {
  local supplied defaults_file endpoint_id override_count model_count effective source
  IFS= read -r supplied
  [ -n "$supplied" ] || { echo 'ERROR: candidate password missing on stdin' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  endpoint_id="$(mysql_scalar "$defaults_file" "SELECT id FROM endpoint WHERE mac_address='C0:74:AD:E8:66:09' AND last_known_ipv4='192.168.1.167' LIMIT 1;")"
  [ -n "$endpoint_id" ] || { echo 'ERROR: target endpoint not found' >&2; exit 1; }
  override_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_properties WHERE id_endpoint=${endpoint_id} AND property_key='http_password';")"
  model_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM model_properties mp JOIN endpoint e ON e.id_model=mp.id_model WHERE e.id=${endpoint_id} AND mp.property_key='http_password';")"
  source='NONE'
  effective=''
  if [ "$override_count" -gt 0 ]; then
    source='ENDPOINT_OVERRIDE'
    effective="$(mysql_scalar "$defaults_file" "SELECT property_value FROM endpoint_properties WHERE id_endpoint=${endpoint_id} AND property_key='http_password' ORDER BY id DESC LIMIT 1;")"
  elif [ "$model_count" -gt 0 ]; then
    source='MODEL_DEFAULT'
    effective="$(mysql_scalar "$defaults_file" "SELECT mp.property_value FROM model_properties mp JOIN endpoint e ON e.id_model=mp.id_model WHERE e.id=${endpoint_id} AND mp.property_key='http_password' ORDER BY mp.id DESC LIMIT 1;")"
  fi
  echo 'scope=READ_ONLY_EFFECTIVE_HTTP_PASSWORD_MATCH'
  echo 'db_write=NO'
  echo 'phone_write=NO'
  echo 'secret_values_logged=NO'
  echo "effective_http_password_source=$source"
  echo "endpoint_override_count=$override_count"
  echo "model_default_count=$model_count"
  if [ -n "$effective" ] && [ "$effective" = "$supplied" ]; then
    echo 'effective_http_password_matches_lab_secret=YES'
    echo 'diagnostic=HTTP_PASSWORD_MATCHES'
  else
    echo 'effective_http_password_matches_lab_secret=NO'
    echo 'diagnostic=HTTP_PASSWORD_MISMATCH'
  fi
  supplied=''; effective=''
  rm -f "$defaults_file"; trap - RETURN EXIT
  echo 'G10-19H8H2F-COMPLETE=YES'
}
'''
s=s.replace(anchor,func+anchor,1)
case_anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8H2F helper case anchor missing')
s=s.replace(case_anchor,case_anchor+'\n  compare-grandstream-http-password) [ -z "$OVERLAY_ROOT" ] || usage; compare_grandstream_http_password ;;',1)
p.write_text(s,encoding='utf-8')
print('G10-19H8H2F-HELPER-PREPARE=PASS')
