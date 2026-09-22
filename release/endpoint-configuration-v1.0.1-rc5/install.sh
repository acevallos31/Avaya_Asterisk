#!/usr/bin/env bash
set -euo pipefail
umask 077
export PYTHONDONTWRITEBYTECODE=1

VERSION='1.0.1-rc5'
NAME='issabel-endpoint-configuration'
STATE_DIR="/var/lib/${NAME}/${VERSION}"
BACKUP_DIR="${STATE_DIR}/backup"
MANIFEST="${STATE_DIR}/runtime.manifest"
INSTALLED="${STATE_DIR}/installed.version"

AMPORTAL_CONF='/etc/amportal.conf'
MODULE='/var/www/html/modules/endpoint_configurator'
ENDPOINT_BASE='/usr/share/issabel/endpoint-classes'
CLI_DST='/usr/local/libexec/issabel-endpoint-credential-vault'
KEY_DST='/etc/issabel/endpoint-configurator.key'
GRANDSTREAM_DST="${ENDPOINT_BASE}/class/issabel/vendor/Grandstream.py"
AVAYA_DST="${ENDPOINT_BASE}/class/issabel/vendor/Avaya.py"
AVAYA_J129_TPL_DST="${ENDPOINT_BASE}/tpl/Avaya_J129.tpl"
AVAYA_GLOBAL_TPL_DST="${ENDPOINT_BASE}/tpl/Avaya_global_SIP.tpl"
AVAYA_HTTP_DST='/etc/httpd/conf.d/avaya-j129-provisioning.conf'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="${SCRIPT_DIR}/payload"
BASE_PAYLOAD="${PAYLOAD}/base"
CRED_PAYLOAD="${PAYLOAD}/credentials"

GRANDSTREAM_SRC="${BASE_PAYLOAD}/Grandstream.py"
CATALOG_SQL="${BASE_PAYLOAD}/grandstream-catalog.sql"
AVAYA_SRC="${BASE_PAYLOAD}/Avaya.py"
AVAYA_J129_TPL_SRC="${BASE_PAYLOAD}/Avaya_J129.tpl"
AVAYA_GLOBAL_TPL_SRC="${BASE_PAYLOAD}/Avaya_global_SIP.tpl"
AVAYA_HTTP_SRC="${BASE_PAYLOAD}/avaya-j129-provisioning.conf"

GOLDEN_PAYLOAD="${PAYLOAD}/golden"
ENDPOINTCONFIG_BIN_SRC="${GOLDEN_PAYLOAD}/issabel-endpointconfig"
BASE_ENDPOINT_SRC="${GOLDEN_PAYLOAD}/BaseEndpoint.py"
SCAN_STATUS_SRC="${GOLDEN_PAYLOAD}/paloEndpointScanStatus.class.php"
ENDPOINTS_LIB_SRC="${GOLDEN_PAYLOAD}/paloSantoEndpoints.class.php"
STANDARD_MANAGER_SRC="${GOLDEN_PAYLOAD}/EndpointManager_Standard.class.php"

ENDPOINTCONFIG_BIN_DST='/usr/bin/issabel-endpointconfig'
BASE_ENDPOINT_DST="${ENDPOINT_BASE}/class/issabel/BaseEndpoint.py"
SCAN_STATUS_DST="${MODULE}/libs/paloEndpointScanStatus.class.php"
ENDPOINTS_LIB_DST="${MODULE}/libs/paloSantoEndpoints.class.php"
STANDARD_MANAGER_DST="${MODULE}/dialogs/standard/EndpointManager_Standard.class.php"

SCHEMA_SQL="${CRED_PAYLOAD}/001_admin_credentials.sql"
KEY_INSTALLER="${CRED_PAYLOAD}/install-key.sh"
VAULT_SRC="${CRED_PAYLOAD}/EndpointCredentialVault.class.php"
CLI_SRC="${CRED_PAYLOAD}/credential-vault-cli.php"
INDEX_SRC="${CRED_PAYLOAD}/index.php"
SUMMARY_SRC="${CRED_PAYLOAD}/summary-index.php"
SUMMARY_LANG_SRC="${CRED_PAYLOAD}/summary-en.lang"
REPORT_SRC="${CRED_PAYLOAD}/reporte_endpoints.tpl"
JS_SRC="${CRED_PAYLOAD}/javascript.js"

GRANDSTREAM_STOCK_SHA256='238f241a7ee394f5c7e4c5d6c998b3f213dc65066a4dd4dd79f073ab0e86cbc7'
GRANDSTREAM_V2_SHA256='f145aa9bba942b9bcd5863bf591e7660e4f805c5a68bbb1b4f235444b99d5441'
CLEAN_BOOTSTRAP_MARKER='RC5-CLEAN-BOOTSTRAP'
AVAYA_SHA256='fcb4eec19d7015cdaf7014c7d05fa179a984ae342b382ee41b069806c2c28ebf'
AVAYA_J129_TPL_SHA256='0c9f60d48db4e105e91ace29909eeb3e168fdb8e16d35427a2ad85227f1fbd08'
AVAYA_GLOBAL_TPL_SHA256='575cc4b290b9919edfbf74d2643dbcaa671565b6d163a8b3856592c5dd00e492'
AVAYA_HTTP_SHA256='9a34bc0e417dc4babcda686d18efa5f9b41a060d892de787cbd56ea24be8ed20'
ENDPOINTCONFIG_BIN_SHA256='2aca894449425f4666a851e6810eb8a51309544d18f3f6fbc563c697cbfe6e32'
BASE_ENDPOINT_SHA256='bf6aefdcca992c02a1981e2b7b4f1829bc87fb01e0efea1ba7b87130ed487814'
SCAN_STATUS_SHA256='0468b326666bf938399cb5aef69c07f43cda645de0fa45cd6b3e72134c3838a8'
ENDPOINTS_LIB_SHA256='f4d8c9150b2709ad3725765bb03eb303427be7b7985cbecfe01b6ae39a76993c'
STANDARD_MANAGER_SHA256='d4217def2e57e472e99a665554a6d560e9dc4e0363ab4d9e2869173d684b9dc9'
UI_INDEX_SHA256='64dced7a1bfe06e2e406d4fd8eddfc717e9f5a7f157ae997d8c288a850cb0c5f'
UI_SUMMARY_SHA256='c15d6a3b2d218b551c450495d8d2ba216244a9239332a57706729f8a700e197f'
UI_SUMMARY_LANG_SHA256='ebd7856ab71df56190391e4e8ed647f3b110614fb6d796e0d58c2212a5cbdf13'
UI_TEMPLATE_SHA256='dc8afe7ac87bda245a4d932e65b17203055c3ce1bfca29846c5de3bc73a0a0a3'
UI_JS_SHA256='51563b6df74aabdefd8b03454ab195bae1c37a639a5bc6d08a7d41508533d4ba'
VAULT_SHA256='186d8faf7231f0a66a70c5929b60ecfa5bf141317f181cf879b813230ae45dd2'
GRANDSTREAM_V2_MARKER='CEIBA-GRANDSTREAM-PROD-V2-GXP16XX'

log(){ printf '[Endpoint Configuration %s] %s\n' "$VERSION" "$*"; }
die(){ printf '[Endpoint Configuration %s] ERROR: %s\n' "$VERSION" "$*" >&2; exit 1; }
need_root(){ [ "$EUID" -eq 0 ] || die 'ejecutar como root'; }
need_file(){ [ -f "$1" ] || die "falta archivo requerido: $1"; }
read_amp(){ sed -n "s/^$1=//p" "$AMPORTAL_CONF" | head -n1; }
escape_mysql(){ local v="$1"; v="${v//\\/\\\\}"; v="${v//\"/\\\"}"; printf '%s' "$v"; }

make_defaults(){
  local u p h f
  need_file "$AMPORTAL_CONF"
  u="$(read_amp AMPDBUSER)"; p="$(read_amp AMPDBPASS)"; h="$(read_amp AMPDBHOST)"
  [ -n "$u" ] || die 'AMPDBUSER no definido'
  [ -n "$p" ] || die 'AMPDBPASS no definido'
  [ -n "$h" ] || h=localhost
  f="$(mktemp /tmp/endpoint-config-rc5-db.XXXXXX.cnf)"; chmod 0600 "$f"
  {
    echo '[client]'
    printf 'user="%s"\n' "$(escape_mysql "$u")"
    printf 'password="%s"\n' "$(escape_mysql "$p")"
    printf 'host="%s"\n' "$(escape_mysql "$h")"
  } > "$f"
  printf '%s' "$f"
}
scalar(){ mysql --defaults-extra-file="$1" --batch --skip-column-names endpointconfig -e "$2"; }

schema_count(){
  scalar "$1" "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='endpointconfig' AND table_name IN ('pbx_admin_password_policy','endpoint_admin_credential','endpoint_credential_event');"
}

verify_schema(){
  local df="$1" count cols
  count="$(schema_count "$df")"
  [ "$count" = 3 ] || die "credential schema table count=$count"
  cols="$(scalar "$df" "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='endpointconfig' AND ((table_name='pbx_admin_password_policy' AND column_name IN ('id','pbx_identity','active_version','pending_version','ciphertext','key_reference','status','created_at','rotated_at')) OR (table_name='endpoint_admin_credential' AND column_name IN ('id_endpoint','source','ciphertext','key_reference','version','validation_status','last_validated_at','rotation_status','updated_at')) OR (table_name='endpoint_credential_event' AND column_name IN ('id','id_endpoint','operation','result','actor','correlation_id','created_at')));")"
  [ "$cols" = 25 ] || die "credential schema column contract mismatch=$cols"
}

bootstrap_schema_with_dba() (
  set -euo pipefail
  umask 077
  local dba_user dba_pass dba_cnf

  if mysql --batch --skip-column-names -e 'SELECT CURRENT_USER();' >/dev/null 2>&1; then
    log 'DBA-AUTH=LOCAL-AUTO'
    mysql endpointconfig < "$SCHEMA_SQL"
    log 'CREDENTIAL-SCHEMA-DBA-INSTALL-PASS'
    exit 0
  fi

  printf 'Usuario DBA MariaDB [root]: ' >&2
  IFS= read -r dba_user
  dba_user="${dba_user:-root}"
  [[ "$dba_user" =~ ^[A-Za-z0-9_.@-]+$ ]] || die 'usuario DBA contiene caracteres no permitidos'

  printf 'Contraseña MariaDB para %s: ' "$dba_user" >&2
  IFS= read -r -s dba_pass
  printf '\n' >&2

  dba_cnf="$(mktemp /tmp/endpoint-config-rc5-dba.XXXXXX.cnf)"
  chmod 0600 "$dba_cnf"
  trap 'rm -f "$dba_cnf"' EXIT HUP INT TERM

  {
    echo '[client]'
    printf 'user="%s"\n' "$(escape_mysql "$dba_user")"
    printf 'password="%s"\n' "$(escape_mysql "$dba_pass")"
  } > "$dba_cnf"

  unset dba_pass
  mysql --defaults-extra-file="$dba_cnf" --batch --skip-column-names -e 'SELECT CURRENT_USER();' >/dev/null ||
    die 'autenticación DBA falló'

  mysql --defaults-extra-file="$dba_cnf" endpointconfig < "$SCHEMA_SQL"
  log 'DBA-AUTH=INTERACTIVE-TEMPORARY'
  log 'CREDENTIAL-SCHEMA-DBA-INSTALL-PASS'

  rm -f "$dba_cnf"
  trap - EXIT HUP INT TERM
)

verify_runtime_dml(){
  local df="$1"
  mysql --defaults-extra-file="$df" endpointconfig <<'SQL' >/dev/null
START TRANSACTION;
INSERT INTO endpoint_credential_event
  (id_endpoint, operation, result, actor, correlation_id, created_at)
VALUES
  (NULL, 'INSTALL_PRIVILEGE_TEST', 'PENDING', 'rc5-installer',
   '00000000-0000-0000-0000-000000000005', NOW());
UPDATE endpoint_credential_event
SET result='PASS'
WHERE correlation_id='00000000-0000-0000-0000-000000000005';
DELETE FROM endpoint_credential_event
WHERE correlation_id='00000000-0000-0000-0000-000000000005';
ROLLBACK;
SQL
  log 'RUNTIME-DB-DML-PASS'
}

check_hash(){
  local file="$1" expected="$2" label="$3" actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  [ "$actual" = "$expected" ] || die "$label sha256 mismatch: $actual"
}

check_payload(){
  local f
  for f in     "$GRANDSTREAM_SRC" "$CATALOG_SQL" "$AVAYA_SRC" "$AVAYA_J129_TPL_SRC" "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_HTTP_SRC"     "$ENDPOINTCONFIG_BIN_SRC" "$BASE_ENDPOINT_SRC" "$SCAN_STATUS_SRC" "$ENDPOINTS_LIB_SRC" "$STANDARD_MANAGER_SRC"     "$SCHEMA_SQL" "$KEY_INSTALLER" "$VAULT_SRC" "$CLI_SRC" "$INDEX_SRC" "$SUMMARY_SRC" "$SUMMARY_LANG_SRC" "$REPORT_SRC" "$JS_SRC"; do
    need_file "$f"
    [ ! -L "$f" ] || die "symlink rechazado en payload: $f"
  done

  bash -n "$KEY_INSTALLER"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$GRANDSTREAM_SRC"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$AVAYA_SRC"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$ENDPOINTCONFIG_BIN_SRC"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$BASE_ENDPOINT_SRC"
  php -l "$SCAN_STATUS_SRC" >/dev/null
  php -l "$ENDPOINTS_LIB_SRC" >/dev/null
  php -l "$STANDARD_MANAGER_SRC" >/dev/null
  php -l "$VAULT_SRC" >/dev/null
  php -l "$CLI_SRC" >/dev/null
  php -l "$INDEX_SRC" >/dev/null
  php -l "$SUMMARY_SRC" >/dev/null

  check_hash "$AVAYA_SRC" "$AVAYA_SHA256" Avaya.py
  check_hash "$AVAYA_J129_TPL_SRC" "$AVAYA_J129_TPL_SHA256" Avaya_J129.tpl
  check_hash "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_GLOBAL_TPL_SHA256" Avaya_global_SIP.tpl
  check_hash "$AVAYA_HTTP_SRC" "$AVAYA_HTTP_SHA256" avaya-j129-provisioning.conf
  check_hash "$ENDPOINTCONFIG_BIN_SRC" "$ENDPOINTCONFIG_BIN_SHA256" issabel-endpointconfig
  check_hash "$BASE_ENDPOINT_SRC" "$BASE_ENDPOINT_SHA256" BaseEndpoint.py
  check_hash "$ENDPOINTS_LIB_SRC" "$ENDPOINTS_LIB_SHA256" paloSantoEndpoints.class.php
  check_hash "$STANDARD_MANAGER_SRC" "$STANDARD_MANAGER_SHA256" EndpointManager_Standard.class.php
  check_hash "$INDEX_SRC" "$UI_INDEX_SHA256" index.php
  check_hash "$SUMMARY_SRC" "$UI_SUMMARY_SHA256" summary-index.php
  check_hash "$SUMMARY_LANG_SRC" "$UI_SUMMARY_LANG_SHA256" summary-en.lang
  check_hash "$REPORT_SRC" "$UI_TEMPLATE_SHA256" reporte_endpoints.tpl
  check_hash "$JS_SRC" "$UI_JS_SHA256" javascript.js
  check_hash "$VAULT_SRC" "$VAULT_SHA256" EndpointCredentialVault.class.php

  grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_SRC" || die 'Grandstream V2 marker missing'
  grep -Fq "_probeModelFromAsterisk" "$GRANDSTREAM_SRC" || die 'clean bootstrap model probe missing'
  grep -Fq "\$cuentasRegistradas[\$ip]['sip'][]" "$SCAN_STATUS_SRC" || die 'clean bootstrap SIP reconciliation missing'
  log 'RC5-CLEAN-BOOTSTRAP-PAYLOAD-PASS'
  grep -Fq 'EndpointCredentialVault.class.php' "$INDEX_SRC" || die 'credential UI missing in index payload'
  grep -Fq 'loadCredentialPolicy' "$JS_SRC" || die 'credential policy controller missing'
  grep -Fq 'endpoint-account-summary' "$REPORT_SRC" || die 'extension/registration column missing'

  log 'CEIBA-GOLDEN-PAYLOAD-PASS'
}

check_grandstream(){
  local sha
  need_file "$GRANDSTREAM_DST"
  sha="$(sha256sum "$GRANDSTREAM_DST" | awk '{print $1}')"
  if cmp -s "$GRANDSTREAM_DST" "$GRANDSTREAM_SRC"; then
    log "Grandstream runtime RC5 clean-bootstrap presente sha256=$sha"
    return 0
  fi
  case "$sha" in
    "$GRANDSTREAM_STOCK_SHA256") log "Grandstream stock compatible sha256=$sha" ;;
    "$GRANDSTREAM_V2_SHA256") log "Grandstream runtime Ceiba V2 presente sha256=$sha" ;;
    *) die "Grandstream.py baseline no soportado: $sha" ;;
  esac
}

web_health(){
  local code
  apachectl -t >/dev/null
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 8 https://127.0.0.1/ || true)"
  [ "$code" != 000 ] && [ "$code" -ge 200 ] 2>/dev/null && [ "$code" -lt 500 ] 2>/dev/null || die "HTTPS local no saludable: ${code:-000}"
  log "WEB-HEALTH-PASS status=$code"
}

preflight(){
  need_root
  local cmd df tables
  for cmd in python3 php mysql curl openssl apachectl install sha256sum mktemp; do
    command -v "$cmd" >/dev/null 2>&1 || die "comando requerido no disponible: $cmd"
  done
  [ -d "$MODULE" ] || die 'Endpoint Configurator web module no encontrado'
  [ -d "$ENDPOINT_BASE" ] || die 'Endpoint classes no encontradas'
  need_file /usr/bin/issabel-endpointconfig
  id asterisk >/dev/null 2>&1 || die 'usuario asterisk no encontrado'
  rpm -q issabel-endpointconfig2-5.0.0-1.el8.noarch >/dev/null 2>&1 ||
    die 'RC4 requiere issabel-endpointconfig2-5.0.0-1.el8.noarch, la misma base auditada en Ceiba'

  check_payload
  check_grandstream
  web_health

  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  tables="$(schema_count "$df")"
  [ "$tables" = 0 ] || [ "$tables" = 3 ] || die "schema de credenciales parcial: $tables/3"
  if [ "$tables" = 3 ]; then
    verify_schema "$df"
    log 'CREDENTIAL-SCHEMA=PRESENT'
  else
    log 'CREDENTIAL-SCHEMA=ABSENT'
    log 'DBA-BOOTSTRAP=REQUIRED-DURING-INSTALL'
  fi
  rm -f "$df"; trap - RETURN EXIT

  if [ -e "$KEY_DST" ]; then
    [ -f "$KEY_DST" ] || die 'credential key path no es archivo regular'
    log "CREDENTIAL-KEY=PRESENT mode=$(stat -c '%U:%G:%a' "$KEY_DST")"
  else
    log 'CREDENTIAL-KEY=ABSENT'
  fi

  log 'PREFLIGHT-PASS'
  log 'phone_write=NO'
  log 'endpoint_discovery=NO'
}

backup_one(){
  local dst="$1" rel
  rel="${dst#/}"
  if [ -e "$dst" ]; then
    install -d -o root -g root -m 0700 "$BACKUP_DIR/$(dirname "$rel")"
    cp -a "$dst" "$BACKUP_DIR/$rel"
    printf 'PRESENT %s\n' "$dst" >> "$MANIFEST"
  else
    printf 'ABSENT %s\n' "$dst" >> "$MANIFEST"
  fi
}

save_state(){
  [ ! -e "$MANIFEST" ] || return 0
  install -d -o root -g root -m 0700 "$STATE_DIR" "$BACKUP_DIR"
  : > "$MANIFEST"; chmod 0600 "$MANIFEST"

  local dst
  for dst in     "$GRANDSTREAM_DST" "$AVAYA_DST" "$AVAYA_J129_TPL_DST" "$AVAYA_GLOBAL_TPL_DST" "$AVAYA_HTTP_DST"     "$ENDPOINTCONFIG_BIN_DST" "$BASE_ENDPOINT_DST" "$SCAN_STATUS_DST" "$ENDPOINTS_LIB_DST" "$STANDARD_MANAGER_DST"     "$MODULE/index.php" "$MODULE/libs/EndpointCredentialVault.class.php"     "$MODULE/dialogs/summary/index.php" "$MODULE/dialogs/summary/lang/en.lang"     "$MODULE/themes/default/reporte_endpoints.tpl" "$MODULE/themes/default/js/javascript.js"     "$CLI_DST"; do
    backup_one "$dst"
  done

  log 'BACKUP-PASS'
}

install_base_runtime(){
  install -o root -g root -m 0644 "$GRANDSTREAM_SRC" "$GRANDSTREAM_DST"
  install -o root -g root -m 0644 "$AVAYA_SRC" "$AVAYA_DST"
  install -o root -g root -m 0644 "$AVAYA_J129_TPL_SRC" "$AVAYA_J129_TPL_DST"
  install -o root -g root -m 0644 "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_GLOBAL_TPL_DST"
  install -o root -g root -m 0644 "$AVAYA_HTTP_SRC" "$AVAYA_HTTP_DST"

  install -o root -g root -m 0755 "$ENDPOINTCONFIG_BIN_SRC" "$ENDPOINTCONFIG_BIN_DST"
  install -o root -g root -m 0755 "$BASE_ENDPOINT_SRC" "$BASE_ENDPOINT_DST"
  install -o asterisk -g asterisk -m 0644 "$SCAN_STATUS_SRC" "$SCAN_STATUS_DST"
  install -o asterisk -g asterisk -m 0644 "$ENDPOINTS_LIB_SRC" "$ENDPOINTS_LIB_DST"
  install -o asterisk -g asterisk -m 0644 "$STANDARD_MANAGER_SRC" "$STANDARD_MANAGER_DST"

  rm -f "${GRANDSTREAM_DST}c" "${AVAYA_DST}c" "${BASE_ENDPOINT_DST}c" 2>/dev/null || true
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$GRANDSTREAM_DST"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$AVAYA_DST"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$ENDPOINTCONFIG_BIN_DST"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$BASE_ENDPOINT_DST"
  php -l "$SCAN_STATUS_DST" >/dev/null
  php -l "$ENDPOINTS_LIB_DST" >/dev/null
  php -l "$STANDARD_MANAGER_DST" >/dev/null

  log 'CEIBA-GOLDEN-RUNTIME-INSTALL-PASS'
}

install_catalog(){
  local df
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  mysql --defaults-extra-file="$df" endpointconfig < "$CATALOG_SQL"
  mysql --defaults-extra-file="$df" endpointconfig <<'SQL'
START TRANSACTION;
INSERT INTO manufacturer (name,description)
SELECT 'Avaya','Avaya IP Phones' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM manufacturer WHERE name='Avaya');
SET @avaya_id := (SELECT id FROM manufacturer WHERE name='Avaya' LIMIT 1);
INSERT INTO model (id_manufacturer,name,description,max_accounts,static_ip_supported,dynamic_ip_supported,static_prov_supported)
SELECT @avaya_id,'J129','Avaya J129',1,1,1,1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM model WHERE id_manufacturer=@avaya_id AND name='J129');
SET @j129_id := (SELECT id FROM model WHERE id_manufacturer=@avaya_id AND name='J129' LIMIT 1);
UPDATE model SET max_accounts=1 WHERE id=@j129_id;
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @j129_id,'max_sip_accounts','1' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM model_properties WHERE id_model=@j129_id AND property_key='max_sip_accounts');
UPDATE model_properties SET property_value='1' WHERE id_model=@j129_id AND property_key='max_sip_accounts';
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @j129_id,'max_iax2_accounts','0' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM model_properties WHERE id_model=@j129_id AND property_key='max_iax2_accounts');
UPDATE model_properties SET property_value='0' WHERE id_model=@j129_id AND property_key='max_iax2_accounts';
INSERT INTO mac_prefix (id_manufacturer,mac_prefix,description)
SELECT @avaya_id,'C8:1F:EA','Avaya J129' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM mac_prefix WHERE UPPER(mac_prefix)='C8:1F:EA');
COMMIT;
SQL
  rm -f "$df"; trap - RETURN EXIT
}

install_credentials(){
  local df tables
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  tables="$(schema_count "$df")"
  rm -f "$df"; trap - RETURN EXIT

  if [ "$tables" = 0 ]; then
    bootstrap_schema_with_dba
  fi

  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  verify_schema "$df"
  verify_runtime_dml "$df"
  rm -f "$df"; trap - RETURN EXIT

  "$KEY_INSTALLER" "$KEY_DST"
  [ "$(stat -c '%U:%G:%a' "$KEY_DST")" = 'root:asterisk:640' ] || die 'credential key ownership/mode mismatch'

  install -d -o root -g root -m 0755 "$MODULE/libs" "$MODULE/dialogs/summary/lang" /usr/local/libexec
  install -o root -g root -m 0644 "$VAULT_SRC" "$MODULE/libs/EndpointCredentialVault.class.php"
  install -o root -g root -m 0644 "$INDEX_SRC" "$MODULE/index.php"
  install -o root -g root -m 0644 "$SUMMARY_SRC" "$MODULE/dialogs/summary/index.php"
  install -o root -g root -m 0644 "$SUMMARY_LANG_SRC" "$MODULE/dialogs/summary/lang/en.lang"
  install -o root -g root -m 0644 "$REPORT_SRC" "$MODULE/themes/default/reporte_endpoints.tpl"
  install -o root -g root -m 0644 "$JS_SRC" "$MODULE/themes/default/js/javascript.js"
  install -o root -g asterisk -m 0750 "$CLI_SRC" "$CLI_DST"

  log 'CREDENTIAL-RUNTIME-INSTALL-PASS'
}

verify_catalog(){
  local df gs g1 g2 p1 p2 av j129 ap
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  gs="$(scalar "$df" "SELECT COUNT(*) FROM manufacturer WHERE name='Grandstream';")"
  g1="$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer f ON f.id=m.id_manufacturer WHERE f.name='Grandstream' AND m.name='GRP2601P' AND m.max_accounts=2;")"
  g2="$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer f ON f.id=m.id_manufacturer WHERE f.name='Grandstream' AND m.name='GRP2602G' AND m.max_accounts=4;")"
  p1="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix p JOIN manufacturer f ON f.id=p.id_manufacturer WHERE f.name='Grandstream' AND UPPER(p.mac_prefix)='C0:74:AD';")"
  p2="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix p JOIN manufacturer f ON f.id=p.id_manufacturer WHERE f.name='Grandstream' AND UPPER(p.mac_prefix)='EC:74:D7';")"
  av="$(scalar "$df" "SELECT COUNT(*) FROM manufacturer WHERE name='Avaya';")"
  j129="$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer f ON f.id=m.id_manufacturer WHERE f.name='Avaya' AND m.name='J129' AND m.max_accounts=1;")"
  ap="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix p JOIN manufacturer f ON f.id=p.id_manufacturer WHERE f.name='Avaya' AND UPPER(p.mac_prefix)='C8:1F:EA';")"
  [ "$gs,$g1,$g2,$p1,$p2,$av,$j129,$ap" = '1,1,1,1,1,1,1,1' ] || die "catalog verify mismatch $gs,$g1,$g2,$p1,$p2,$av,$j129,$ap"
  rm -f "$df"; trap - RETURN EXIT
}

verify(){
  need_root
  local df
  check_payload
  check_hash "$AVAYA_DST" "$AVAYA_SHA256" live-Avaya.py
  check_hash "$AVAYA_J129_TPL_DST" "$AVAYA_J129_TPL_SHA256" live-Avaya_J129.tpl
  check_hash "$AVAYA_GLOBAL_TPL_DST" "$AVAYA_GLOBAL_TPL_SHA256" live-Avaya_global_SIP.tpl
  check_hash "$AVAYA_HTTP_DST" "$AVAYA_HTTP_SHA256" live-avaya-http
  check_hash "$ENDPOINTCONFIG_BIN_DST" "$ENDPOINTCONFIG_BIN_SHA256" live-issabel-endpointconfig
  check_hash "$BASE_ENDPOINT_DST" "$BASE_ENDPOINT_SHA256" live-BaseEndpoint.py
  check_hash "$ENDPOINTS_LIB_DST" "$ENDPOINTS_LIB_SHA256" live-paloSantoEndpoints
  check_hash "$STANDARD_MANAGER_DST" "$STANDARD_MANAGER_SHA256" live-EndpointManager_Standard
  check_hash "$MODULE/index.php" "$UI_INDEX_SHA256" live-index.php
  check_hash "$MODULE/dialogs/summary/index.php" "$UI_SUMMARY_SHA256" live-summary
  check_hash "$MODULE/dialogs/summary/lang/en.lang" "$UI_SUMMARY_LANG_SHA256" live-summary-lang
  check_hash "$MODULE/themes/default/reporte_endpoints.tpl" "$UI_TEMPLATE_SHA256" live-template
  check_hash "$MODULE/themes/default/js/javascript.js" "$UI_JS_SHA256" live-javascript
  check_hash "$MODULE/libs/EndpointCredentialVault.class.php" "$VAULT_SHA256" live-vault

  cmp -s "$GRANDSTREAM_SRC" "$GRANDSTREAM_DST" || die 'Grandstream clean-bootstrap runtime mismatch'
  cmp -s "$SCAN_STATUS_SRC" "$SCAN_STATUS_DST" || die 'Endpoint scan clean-bootstrap runtime mismatch'
  grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST" || die 'Grandstream V2 runtime missing'
  grep -Fq "_probeModelFromAsterisk" "$GRANDSTREAM_DST" || die 'clean bootstrap model probe missing'
  grep -Fq "\$cuentasRegistradas[\$ip]['sip'][]" "$SCAN_STATUS_DST" || die 'clean bootstrap SIP reconciliation missing'
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$GRANDSTREAM_DST"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$AVAYA_DST"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$ENDPOINTCONFIG_BIN_DST"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$BASE_ENDPOINT_DST"

  cmp -s "$AVAYA_SRC" "$AVAYA_DST" || die 'Avaya.py runtime mismatch'
  cmp -s "$INDEX_SRC" "$MODULE/index.php" || die 'Endpoint UI index mismatch'
  cmp -s "$SUMMARY_SRC" "$MODULE/dialogs/summary/index.php" || die 'summary dialog mismatch'
  cmp -s "$REPORT_SRC" "$MODULE/themes/default/reporte_endpoints.tpl" || die 'endpoint report template mismatch'
  cmp -s "$JS_SRC" "$MODULE/themes/default/js/javascript.js" || die 'endpoint javascript mismatch'
  cmp -s "$VAULT_SRC" "$MODULE/libs/EndpointCredentialVault.class.php" || die 'credential vault runtime mismatch'
  cmp -s "$CLI_SRC" "$CLI_DST" || die 'credential CLI runtime mismatch'

  [ "$(stat -c '%U:%G:%a' "$KEY_DST")" = 'root:asterisk:640' ] || die 'credential key invalid'
  [ "$(stat -c '%U:%G:%a' "$CLI_DST")" = 'root:asterisk:750' ] || die 'credential CLI ownership/mode invalid'

  php -l "$MODULE/index.php" >/dev/null
  php -l "$MODULE/dialogs/summary/index.php" >/dev/null
  php -l "$MODULE/libs/EndpointCredentialVault.class.php" >/dev/null
  php -l "$CLI_DST" >/dev/null
  apachectl -t >/dev/null

  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  verify_schema "$df"
  rm -f "$df"; trap - RETURN EXIT
  verify_catalog
  web_health

  log 'CEIBA-GOLDEN-SHA-PARITY-PASS'
  log 'RC5-CLEAN-BOOTSTRAP-PASS'
  log 'VERIFY-PASS'
  log 'ui_extension_registration=YES'
  log 'ui_admin_security=YES'
  log 'credential_vault=YES'
  log 'supported_grandstream=GXP1625,GRP2601P,GRP2602G'
  log 'supported_avaya=J129'
  log 'phone_write=NO'
  log 'endpoint_discovery=NO'
}

install_all(){
  preflight
  save_state

  local installing=1
  trap 'rc=$?; if [ "$installing" -eq 1 ]; then echo "[Endpoint Configuration 1.0.1-rc5] ERROR: restaurando runtime desde backup RC4" >&2; restore_runtime || true; apachectl -t >/dev/null 2>&1 && systemctl reload httpd || true; fi; exit "$rc"' ERR

  # El esquema se crea con una sesión DBA temporal cuando todavía no existe.
  # La contraseña DBA nunca se pasa por argv ni se persiste después del bootstrap.
  install_credentials
  install_base_runtime
  install_catalog
  apachectl -t >/dev/null
  systemctl reload httpd

  printf '%s\n' "$VERSION" > "$INSTALLED"
  chmod 0600 "$INSTALLED"
  verify

  installing=0
  trap - ERR
  log 'INSTALL-PASS'
  log 'IMPORTANTE: discovery y Configure siguen siendo operaciones manuales.'
}

restore_runtime(){
  local state dst rel
  [ -f "$MANIFEST" ] || die 'no existe manifest RC4 de backup'
  while read -r state dst; do
    rel="${dst#/}"
    case "$state" in
      PRESENT)
        [ -e "$BACKUP_DIR/$rel" ] || die "backup faltante: $dst"
        install -d -m 0755 "$(dirname "$dst")"
        cp -a "$BACKUP_DIR/$rel" "$dst"
        ;;
      ABSENT) rm -f "$dst" ;;
      *) die "estado inválido en manifest: $state" ;;
    esac
  done < "$MANIFEST"
}

rollback(){
  need_root
  restore_runtime
  apachectl -t >/dev/null
  systemctl reload httpd
  rm -f "$INSTALLED"
  log 'ROLLBACK-RUNTIME-PASS'
  log 'schema_rollback=NO'
  log 'credential_key_removal=NO'
  log 'catalog_rollback=NO'
  log 'phone_write=NO'
}

status(){
  printf 'version=%s\n' "$VERSION"
  [ -f "$INSTALLED" ] && printf 'installed=YES\n' || printf 'installed=NO\n'
  [ -f "$MODULE/libs/EndpointCredentialVault.class.php" ] && printf 'credential_vault=YES\n' || printf 'credential_vault=NO\n'
  grep -Fq 'endpoint-account-summary' "$MODULE/themes/default/reporte_endpoints.tpl" 2>/dev/null && printf 'extension_registration_ui=YES\n' || printf 'extension_registration_ui=NO\n'
  grep -Fq 'loadCredentialPolicy' "$MODULE/themes/default/js/javascript.js" 2>/dev/null && printf 'admin_security_ui=YES\n' || printf 'admin_security_ui=NO\n'
}

usage(){
  cat <<'EOF'
Uso:
  sudo bash install.sh preflight
  sudo bash install.sh install
  sudo bash install.sh verify
  sudo bash install.sh rollback
  bash install.sh status

RC5 instala la imagen dorada auditada de Ceiba más el bootstrap para una central limpia:
- Grandstream V2
- Avaya J129
- Extension / Registration
- seguridad administrativa y vault cifrado

Conserva el runtime auditado de Ceiba y agrega únicamente detección read-only de modelo por Useragent y reconciliación IP->extensión durante discovery. NO ejecuta discovery automáticamente y NO configura/reinicia teléfonos.
EOF
}

case "${1:-}" in
  preflight) preflight ;;
  install) install_all ;;
  verify) verify ;;
  rollback) rollback ;;
  status) status ;;
  help|-h|--help|'') usage ;;
  *) usage; exit 2 ;;
esac
