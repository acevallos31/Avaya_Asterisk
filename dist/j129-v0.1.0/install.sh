#!/usr/bin/env bash
set -euo pipefail

# Este instalador se ejecuta como root desde los workflows LAB. Impedir que
# Python escriba __pycache__ dentro del checkout del self-hosted runner.
export PYTHONDONTWRITEBYTECODE=1

PATCH_VERSION="0.1.0"
PATCH_NAME="avaya-j129-issabel"
STATE_DIR="/var/lib/${PATCH_NAME}/${PATCH_VERSION}"
BACKUP_DIR="${STATE_DIR}/backup"
STATE_FILE="${STATE_DIR}/state.env"
AMPORTAL_CONF="/etc/amportal.conf"
BASE="/usr/share/issabel/endpoint-classes"
VENDOR_DST="${BASE}/class/issabel/vendor/Avaya.py"
TPL_J129_DST="${BASE}/tpl/Avaya_J129.tpl"
TPL_GLOBAL_DST="${BASE}/tpl/Avaya_global_SIP.tpl"
HTTP_DST="/etc/httpd/conf.d/avaya-j129-provisioning.conf"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PAYLOAD="${REPO_ROOT}/deploy/j129"
VENDOR_SRC="${PAYLOAD}/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
TPL_J129_SRC="${PAYLOAD}/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl"
TPL_GLOBAL_SRC="${PAYLOAD}/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl"
HTTP_SRC="${PAYLOAD}/httpd/avaya-j129-provisioning.conf"

log(){ printf '[J129-PATCH %s] %s\n' "$PATCH_VERSION" "$*"; }
die(){ printf '[J129-PATCH %s] ERROR: %s\n' "$PATCH_VERSION" "$*" >&2; exit 1; }
need_root(){ [ "${EUID}" -eq 0 ] || die 'ejecutar como root'; }
need_file(){ [ -f "$1" ] || die "falta archivo requerido: $1"; }
read_amp(){ sed -n "s/^$1=//p" "$AMPORTAL_CONF" | head -n1; }
escape_mysql(){ local v="$1"; v="${v//\\/\\\\}"; v="${v//\"/\\\"}"; printf '%s' "$v"; }

make_defaults(){
  local u p h f
  command -v mysql >/dev/null 2>&1 || die 'cliente mysql no disponible'
  need_file "$AMPORTAL_CONF"
  u="$(read_amp AMPDBUSER)"; p="$(read_amp AMPDBPASS)"; h="$(read_amp AMPDBHOST)"
  [ -n "$u" ] || die 'AMPDBUSER no definido'; [ -n "$p" ] || die 'AMPDBPASS no definido'; [ -n "$h" ] || h=localhost
  f="$(mktemp /tmp/j129-patch-db.XXXXXX.cnf)"; chmod 0600 "$f"
  { echo '[client]'; printf 'user="%s"\n' "$(escape_mysql "$u")"; printf 'password="%s"\n' "$(escape_mysql "$p")"; printf 'host="%s"\n' "$(escape_mysql "$h")"; } > "$f"
  printf '%s' "$f"
}
scalar(){ mysql --defaults-extra-file="$1" --batch --skip-column-names endpointconfig -e "$2"; }

preflight(){
  need_root
  [ -d "$BASE" ] || die "Endpoint Configurator no encontrado en $BASE"
  need_file /usr/bin/issabel-endpointconfig
  need_file "$VENDOR_SRC"; need_file "$TPL_J129_SRC"; need_file "$TPL_GLOBAL_SRC"; need_file "$HTTP_SRC"
  command -v python3 >/dev/null 2>&1 || die 'python3 no disponible'
  command -v apachectl >/dev/null 2>&1 || die 'apachectl no disponible'
  python3 -B -c "import ast; ast.parse(open('$VENDOR_SRC', encoding='utf-8').read(), filename='$VENDOR_SRC')"
  local df mf model bad_prefix assigned
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  mf="$(scalar "$df" "SELECT COUNT(*) FROM manufacturer WHERE name='Avaya';")"; [ "$mf" -le 1 ] || die 'fabricante Avaya duplicado'
  model="$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")"; [ "$model" -le 1 ] || die 'modelo J129 duplicado'
  bad_prefix="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix mp LEFT JOIN manufacturer mf ON mf.id=mp.id_manufacturer WHERE mp.mac_prefix='C8:1F:EA' AND COALESCE(mf.name,'')<>'Avaya';")"; [ "$bad_prefix" -eq 0 ] || die 'OUI C8:1F:EA pertenece a otro fabricante'
  assigned="$(scalar "$df" "SELECT COUNT(*) FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint JOIN manufacturer mf ON mf.id=e.id_manufacturer LEFT JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129';")"
  [ "$assigned" -le 1 ] || die 'J129 tiene mas de una cuenta asignada; el parche v1 no migrara multicuenta automaticamente'
  rm -f "$df"; trap - RETURN EXIT
  log 'PREFLIGHT-PASS'
}

backup_file(){
  local src="$1" backup="$2" key="$3"
  if [ -e "$src" ]; then cp -a "$src" "$backup"; printf '%s=present\n' "$key" >> "$STATE_FILE"; else printf '%s=absent\n' "$key" >> "$STATE_FILE"; fi
}

save_state(){
  [ ! -f "$STATE_FILE" ] || return 0
  install -d -m 0700 "$BACKUP_DIR"
  : > "$STATE_FILE"; chmod 0600 "$STATE_FILE"
  backup_file "$VENDOR_DST" "${BACKUP_DIR}/Avaya.py" file_vendor
  backup_file "$TPL_J129_DST" "${BACKUP_DIR}/Avaya_J129.tpl" file_j129
  backup_file "$TPL_GLOBAL_DST" "${BACKUP_DIR}/Avaya_global_SIP.tpl" file_global
  backup_file "$HTTP_DST" "${BACKUP_DIR}/avaya-j129-provisioning.conf" file_http
  local df
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  printf 'db_manufacturer_preexisting=%s\n' "$(scalar "$df" "SELECT COUNT(*) FROM manufacturer WHERE name='Avaya';")" >> "$STATE_FILE"
  printf 'db_model_preexisting=%s\n' "$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")" >> "$STATE_FILE"
  printf 'db_prefix_preexisting=%s\n' "$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix mp JOIN manufacturer mf ON mf.id=mp.id_manufacturer WHERE mf.name='Avaya' AND mp.mac_prefix='C8:1F:EA';")" >> "$STATE_FILE"
  printf 'db_sip_preexisting=%s\n' "$(scalar "$df" "SELECT COUNT(*) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts';")" >> "$STATE_FILE"
  printf 'db_iax_preexisting=%s\n' "$(scalar "$df" "SELECT COUNT(*) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts';")" >> "$STATE_FILE"
  printf 'db_old_max_accounts=%s\n' "$(scalar "$df" "SELECT COALESCE(MAX(m.max_accounts),0) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")" >> "$STATE_FILE"
  printf 'db_old_max_sip=%s\n' "$(scalar "$df" "SELECT COALESCE(MAX(mp.property_value),0) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts';")" >> "$STATE_FILE"
  printf 'db_old_max_iax=%s\n' "$(scalar "$df" "SELECT COALESCE(MAX(mp.property_value),0) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts';")" >> "$STATE_FILE"
  rm -f "$df"; trap - RETURN EXIT
}

install_db(){
  local df; df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  mysql --defaults-extra-file="$df" endpointconfig <<'SQL'
START TRANSACTION;
INSERT INTO manufacturer (name,description)
SELECT 'Avaya','Avaya IP Phones' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM manufacturer WHERE name='Avaya');
SET @avaya_id := (SELECT id FROM manufacturer WHERE name='Avaya' LIMIT 1);
INSERT INTO model (id_manufacturer,name,description,max_accounts,static_ip_supported,dynamic_ip_supported,static_prov_supported)
SELECT @avaya_id,'J129','Avaya J129',1,1,1,1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM model WHERE id_manufacturer=@avaya_id AND name='J129');
SET @j129_id := (SELECT id FROM model WHERE id_manufacturer=@avaya_id AND name='J129' LIMIT 1);
UPDATE model SET max_accounts=1 WHERE id=@j129_id;
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @j129_id,'max_sip_accounts','1' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM model_properties WHERE id_model=@j129_id AND property_key='max_sip_accounts');
UPDATE model_properties SET property_value='1' WHERE id_model=@j129_id AND property_key='max_sip_accounts';
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @j129_id,'max_iax2_accounts','0' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM model_properties WHERE id_model=@j129_id AND property_key='max_iax2_accounts');
UPDATE model_properties SET property_value='0' WHERE id_model=@j129_id AND property_key='max_iax2_accounts';
INSERT INTO mac_prefix (id_manufacturer,mac_prefix,description)
SELECT @avaya_id,'C8:1F:EA','Avaya J129' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM mac_prefix WHERE mac_prefix='C8:1F:EA');
COMMIT;
SQL
  rm -f "$df"; trap - RETURN EXIT
}

verify(){
  need_root
  cmp -s "$VENDOR_SRC" "$VENDOR_DST" || die 'Avaya.py no coincide con payload'
  cmp -s "$TPL_J129_SRC" "$TPL_J129_DST" || die 'Avaya_J129.tpl no coincide con payload'
  cmp -s "$TPL_GLOBAL_SRC" "$TPL_GLOBAL_DST" || die 'Avaya_global_SIP.tpl no coincide con payload'
  cmp -s "$HTTP_SRC" "$HTTP_DST" || die 'config Apache no coincide con payload'
  python3 -B -c "import ast; ast.parse(open('$VENDOR_DST', encoding='utf-8').read(), filename='$VENDOR_DST')"
  apachectl -t
  local df model maxa sip iax prefix
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  model="$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")"
  maxa="$(scalar "$df" "SELECT m.max_accounts FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' LIMIT 1;")"
  sip="$(scalar "$df" "SELECT mp.property_value FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts' LIMIT 1;")"
  iax="$(scalar "$df" "SELECT mp.property_value FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts' LIMIT 1;")"
  prefix="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix mp JOIN manufacturer mf ON mf.id=mp.id_manufacturer WHERE mf.name='Avaya' AND mp.mac_prefix='C8:1F:EA';")"
  [ "$model" = 1 ] && [ "$maxa" = 1 ] && [ "$sip" = 1 ] && [ "$iax" = 0 ] && [ "$prefix" = 1 ] || die 'validacion DB fallo'
  rm -f "$df"; trap - RETURN EXIT
  log 'VERIFY-PASS'
}

install_patch(){
  preflight; save_state
  install -o root -g root -m 0644 "$VENDOR_SRC" "$VENDOR_DST"
  install -o root -g root -m 0644 "$TPL_J129_SRC" "$TPL_J129_DST"
  install -o root -g root -m 0644 "$TPL_GLOBAL_SRC" "$TPL_GLOBAL_DST"
  install -o root -g root -m 0644 "$HTTP_SRC" "$HTTP_DST"
  apachectl -t || die 'Apache invalido tras copiar archivos; ejecutar rollback'
  systemctl reload httpd
  install_db
  printf '%s\n' "$PATCH_VERSION" > "${STATE_DIR}/installed.version"
  verify
  log 'INSTALL-PASS'
}

restore_file(){ local dst="$1" backup="$2" status="$3"; if [ "$status" = present ]; then cp -a "$backup" "$dst"; else rm -f "$dst"; fi; }

rollback(){
  need_root; need_file "$STATE_FILE"
  # shellcheck disable=SC1090
  . "$STATE_FILE"
  restore_file "$VENDOR_DST" "${BACKUP_DIR}/Avaya.py" "$file_vendor"
  restore_file "$TPL_J129_DST" "${BACKUP_DIR}/Avaya_J129.tpl" "$file_j129"
  restore_file "$TPL_GLOBAL_DST" "${BACKUP_DIR}/Avaya_global_SIP.tpl" "$file_global"
  restore_file "$HTTP_DST" "${BACKUP_DIR}/avaya-j129-provisioning.conf" "$file_http"
  apachectl -t; systemctl reload httpd
  local df endpoint_count
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  endpoint_count="$(scalar "$df" "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer WHERE mf.name='Avaya';")"
  if [ "${db_model_preexisting:-0}" = 1 ]; then
    mysql --defaults-extra-file="$df" endpointconfig -e "SET @id=(SELECT m.id FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' LIMIT 1); UPDATE model SET max_accounts=${db_old_max_accounts} WHERE id=@id;"
    if [ "${db_sip_preexisting:-0}" = 1 ]; then mysql --defaults-extra-file="$df" endpointconfig -e "UPDATE model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer SET mp.property_value='${db_old_max_sip}' WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts';"; else mysql --defaults-extra-file="$df" endpointconfig -e "DELETE mp FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts';"; fi
    if [ "${db_iax_preexisting:-0}" = 1 ]; then mysql --defaults-extra-file="$df" endpointconfig -e "UPDATE model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer SET mp.property_value='${db_old_max_iax}' WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts';"; else mysql --defaults-extra-file="$df" endpointconfig -e "DELETE mp FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts';"; fi
  elif [ "$endpoint_count" -eq 0 ]; then
    mysql --defaults-extra-file="$df" endpointconfig <<'SQL'
START TRANSACTION;
SET @mid := (SELECT m.id FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' LIMIT 1);
DELETE FROM model_properties WHERE id_model=@mid;
DELETE FROM model WHERE id=@mid;
DELETE mp FROM mac_prefix mp JOIN manufacturer mf ON mf.id=mp.id_manufacturer WHERE mf.name='Avaya' AND mp.mac_prefix='C8:1F:EA';
DELETE FROM manufacturer WHERE name='Avaya' AND NOT EXISTS (SELECT 1 FROM model WHERE id_manufacturer=manufacturer.id);
COMMIT;
SQL
  else
    log 'ROLLBACK-DB-PARTIAL: metadata J129 conservada porque existen endpoints Avaya'
  fi
  rm -f "$df"; trap - RETURN EXIT
  rm -f "${STATE_DIR}/installed.version"
  log 'ROLLBACK-PASS'
}

usage(){ echo "Uso: $0 {preflight|install|verify|rollback}" >&2; exit 2; }
case "${1:-}" in preflight) preflight ;; install) install_patch ;; verify) verify ;; rollback) rollback ;; *) usage ;; esac