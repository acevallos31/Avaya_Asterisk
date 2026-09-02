#!/usr/bin/env python3
from pathlib import Path

path = Path('deploy/j129/avaya-j129-lab-deploy')
text = path.read_text()

if 'run_rescan_idempotency_audit()' in text:
    print('RESCAN-IDEMPOTENCY-AUDIT-PREPARE-PASS')
    raise SystemExit(0)

anchor = '\ninstall_http_j129() {'
if anchor not in text:
    raise SystemExit('ERROR: no se encontro ancla para insertar auditoria de rescan')

func = r'''

run_rescan_idempotency_audit() {
  local defaults_file mac='C8:1F:EA:9B:65:0D' count endpoint_id expected_ip manufacturer model account_count accounts network sock
  command -v /usr/bin/issabel-helper >/dev/null 2>&1 || { echo 'ERROR: issabel-helper no disponible' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT

  count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE mac_address='${mac}';")"
  [ "$count" -eq 1 ] || { echo "ERROR: antes del rescan se esperaba 1 endpoint para ${mac}; encontrado=${count}" >&2; exit 1; }

  endpoint_id="$(mysql_scalar "$defaults_file" "SELECT id FROM endpoint WHERE mac_address='${mac}' LIMIT 1;")"
  expected_ip="$(mysql_scalar "$defaults_file" "SELECT last_known_ipv4 FROM endpoint WHERE mac_address='${mac}' LIMIT 1;")"
  manufacturer="$(mysql_scalar "$defaults_file" "SELECT mf.name FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer WHERE e.mac_address='${mac}' LIMIT 1;")"
  model="$(mysql_scalar "$defaults_file" "SELECT m.name FROM endpoint e LEFT JOIN model m ON m.id=e.id_model WHERE e.mac_address='${mac}' LIMIT 1;")"
  account_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint WHERE e.mac_address='${mac}';")"
  accounts="$(mysql_scalar "$defaults_file" "SELECT COALESCE(GROUP_CONCAT(ea.account ORDER BY ea.priority SEPARATOR ','),'') FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint WHERE e.mac_address='${mac}';")"

  [ -n "$expected_ip" ] || { echo 'ERROR: endpoint sin last_known_ipv4' >&2; exit 1; }
  [ "$manufacturer" = 'Avaya' ] || { echo "ERROR: fabricante inesperado: $manufacturer" >&2; exit 1; }
  [ "$model" = 'J129' ] || { echo "ERROR: modelo inesperado: $model" >&2; exit 1; }

  network="$(python3 - "$expected_ip" <<'PY'
import ipaddress, sys
ip = ipaddress.ip_address(sys.argv[1])
print(ipaddress.ip_network(str(ip) + '/24', strict=False))
PY
)"

  echo '=== J129 RESCAN IDEMPOTENCY AUDIT ==='
  echo "MAC=${mac}"
  echo "Endpoint ID inicial=${endpoint_id}"
  echo "IP inicial=${expected_ip}"
  echo "Fabricante=${manufacturer} Modelo=${model}"
  echo "Cuentas iniciales=${account_count} [${accounts}]"
  echo "Red de escaneo=${network}"

  run_one_scan() {
    local n="$1" current_count current_id current_ip current_manufacturer current_model current_account_count current_accounts
    echo "=== RESCAN ${n} ==="
    sock="$(/usr/bin/issabel-helper detect_endpoints "$network" 2>&1 | head -n 1)"
    [ -n "$sock" ] || { echo "ERROR: detect_endpoints no devolvio socket en rescan ${n}" >&2; exit 1; }
    echo "Scan iniciado; esperando descubrimiento..."
    sleep 20

    current_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE mac_address='${mac}';")"
    current_id="$(mysql_scalar "$defaults_file" "SELECT id FROM endpoint WHERE mac_address='${mac}' LIMIT 1;")"
    current_ip="$(mysql_scalar "$defaults_file" "SELECT last_known_ipv4 FROM endpoint WHERE mac_address='${mac}' LIMIT 1;")"
    current_manufacturer="$(mysql_scalar "$defaults_file" "SELECT mf.name FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer WHERE e.mac_address='${mac}' LIMIT 1;")"
    current_model="$(mysql_scalar "$defaults_file" "SELECT m.name FROM endpoint e LEFT JOIN model m ON m.id=e.id_model WHERE e.mac_address='${mac}' LIMIT 1;")"
    current_account_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint WHERE e.mac_address='${mac}';")"
    current_accounts="$(mysql_scalar "$defaults_file" "SELECT COALESCE(GROUP_CONCAT(ea.account ORDER BY ea.priority SEPARATOR ','),'') FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint WHERE e.mac_address='${mac}';")"

    echo "Endpoint count=${current_count} id=${current_id} ip=${current_ip} fabricante=${current_manufacturer} modelo=${current_model} cuentas=${current_account_count} [${current_accounts}]"

    [ "$current_count" -eq 1 ] || { echo "ERROR: rescan ${n} creo endpoint duplicado" >&2; exit 1; }
    [ "$current_id" = "$endpoint_id" ] || { echo "ERROR: rescan ${n} cambio el endpoint ID" >&2; exit 1; }
    [ "$current_ip" = "$expected_ip" ] || { echo "ERROR: rescan ${n} cambio inesperadamente la IP" >&2; exit 1; }
    [ "$current_manufacturer" = "$manufacturer" ] || { echo "ERROR: rescan ${n} cambio fabricante" >&2; exit 1; }
    [ "$current_model" = "$model" ] || { echo "ERROR: rescan ${n} cambio modelo" >&2; exit 1; }
    [ "$current_account_count" = "$account_count" ] || { echo "ERROR: rescan ${n} cambio cantidad de cuentas" >&2; exit 1; }
    [ "$current_accounts" = "$accounts" ] || { echo "ERROR: rescan ${n} cambio cuentas asignadas" >&2; exit 1; }
  }

  run_one_scan 1
  run_one_scan 2

  rm -f "$defaults_file"; trap - RETURN EXIT
  echo 'J129-RESCAN-IDEMPOTENCY-AUDIT-PASS'
}
'''

text = text.replace(anchor, func + anchor, 1)
case_anchor = '  inspect-sip-registration) [ -z "$OVERLAY_ROOT" ] || usage; run_sip_registration_inspection ;;'
if case_anchor not in text:
    raise SystemExit('ERROR: no se encontro ancla del case')
text = text.replace(case_anchor, case_anchor + '\n  audit-rescan-idempotency) [ -z "$OVERLAY_ROOT" ] || usage; run_rescan_idempotency_audit ;;', 1)
path.write_text(text)
print('RESCAN-IDEMPOTENCY-AUDIT-PREPARE-PASS')
