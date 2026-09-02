from pathlib import Path

path = Path('deploy/j129/avaya-j129-lab-deploy')
text = path.read_text()

marker = '[ -n "$ACTION" ] || usage\ncase "$ACTION" in\n'
if marker not in text:
    raise SystemExit('No se encontro el case principal del helper')

function = r'''
apply_v1_single_account() {
  local defaults_file model_count account_count max_accounts max_sip account_list
  defaults_file="$(make_db_defaults_file)"
  trap 'rm -f "$defaults_file"' RETURN EXIT

  model_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")"
  [ "$model_count" -eq 1 ] || { echo "ERROR: se esperaba exactamente un modelo Avaya J129" >&2; exit 1; }

  account_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129';")"
  [ "$account_count" -le 1 ] || { echo "ERROR: existen mas de una cuenta asignada al J129; no se aplica el limite v1 automaticamente" >&2; exit 1; }

  mysql --defaults-extra-file="$defaults_file" endpointconfig <<'SQL'
START TRANSACTION;
SET @j129_id := (
  SELECT m.id
  FROM model m
  JOIN manufacturer mf ON mf.id=m.id_manufacturer
  WHERE mf.name='Avaya' AND m.name='J129'
  LIMIT 1
);
UPDATE model SET max_accounts=1 WHERE id=@j129_id;
INSERT INTO model_properties (id_model, property_key, property_value)
SELECT @j129_id, 'max_sip_accounts', '1'
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM model_properties
  WHERE id_model=@j129_id AND property_key='max_sip_accounts'
);
UPDATE model_properties
SET property_value='1'
WHERE id_model=@j129_id AND property_key='max_sip_accounts';
COMMIT;
SQL

  max_accounts="$(mysql_scalar "$defaults_file" "SELECT m.max_accounts FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' LIMIT 1;")"
  max_sip="$(mysql_scalar "$defaults_file" "SELECT mp.property_value FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts' LIMIT 1;")"
  account_list="$(mysql_scalar "$defaults_file" "SELECT COALESCE(GROUP_CONCAT(ea.account ORDER BY ea.priority SEPARATOR ','),'') FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129';")"

  echo '=== J129 V1 SINGLE ACCOUNT ==='
  echo "max_accounts=$max_accounts"
  echo "max_sip_accounts=$max_sip"
  echo "cuentas_asignadas=$account_count [$account_list]"

  [ "$max_accounts" = '1' ] || { echo 'J129-V1-SINGLE-ACCOUNT-FAIL'; exit 1; }
  [ "$max_sip" = '1' ] || { echo 'J129-V1-SINGLE-ACCOUNT-FAIL'; exit 1; }
  [ "$account_count" -le 1 ] || { echo 'J129-V1-SINGLE-ACCOUNT-FAIL'; exit 1; }

  rm -f "$defaults_file"
  trap - RETURN EXIT
  echo 'J129-V1-SINGLE-ACCOUNT-PASS'
}

'''

if 'apply_v1_single_account()' not in text:
    text = text.replace(marker, function + marker)

case_marker = 'case "$ACTION" in\n'
case_line = '  apply-v1-single-account) [ -z "$OVERLAY_ROOT" ] || usage; apply_v1_single_account ;;\n'
if case_line not in text:
    text = text.replace(case_marker, case_marker + case_line, 1)

path.write_text(text)
print('SINGLE-ACCOUNT-V1-PREPARE-PASS')
