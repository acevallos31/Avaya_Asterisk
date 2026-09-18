#!/usr/bin/env bash
set -euo pipefail
umask 077
export PYTHONDONTWRITEBYTECODE=1

VERSION='1.0.1-rc2'
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

PATCHER="${BASE_PAYLOAD}/grandstream-vendor-patch.py"
CATALOG_SQL="${BASE_PAYLOAD}/grandstream-catalog.sql"
AVAYA_SRC="${BASE_PAYLOAD}/Avaya.py"
AVAYA_J129_TPL_SRC="${BASE_PAYLOAD}/Avaya_J129.tpl"
AVAYA_GLOBAL_TPL_SRC="${BASE_PAYLOAD}/Avaya_global_SIP.tpl"
AVAYA_HTTP_SRC="${BASE_PAYLOAD}/avaya-j129-provisioning.conf"

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
  f="$(mktemp /tmp/endpoint-config-rc2-db.XXXXXX.cnf)"; chmod 0600 "$f"
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

check_payload(){
  local f
  for f in     "$PATCHER" "$CATALOG_SQL" "$AVAYA_SRC" "$AVAYA_J129_TPL_SRC" "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_HTTP_SRC"     "$SCHEMA_SQL" "$KEY_INSTALLER" "$VAULT_SRC" "$CLI_SRC" "$INDEX_SRC" "$SUMMARY_SRC" "$SUMMARY_LANG_SRC" "$REPORT_SRC" "$JS_SRC"; do
    need_file "$f"
    [ ! -L "$f" ] || die "symlink rechazado en payload: $f"
  done

  bash -n "$KEY_INSTALLER"
  python3 -B -m py_compile "$PATCHER"
  python3 -B -m py_compile "$AVAYA_SRC"
  php -l "$VAULT_SRC" >/dev/null
  php -l "$CLI_SRC" >/dev/null
  php -l "$INDEX_SRC" >/dev/null
  php -l "$SUMMARY_SRC" >/dev/null

  grep -Fq "$GRANDSTREAM_V2_MARKER" "$PATCHER" || die 'patcher V2 marker missing'
  grep -Fq 'EndpointCredentialVault.class.php' "$INDEX_SRC" || die 'credential UI missing in index payload'
  grep -Fq 'loadCredentialPolicy' "$JS_SRC" || die 'credential policy controller missing'
  grep -Fq 'endpoint-account-summary' "$REPORT_SRC" || die 'extension/registration column missing'
}

check_grandstream(){
  local sha
  need_file "$GRANDSTREAM_DST"
  sha="$(sha256sum "$GRANDSTREAM_DST" | awk '{print $1}')"
  if grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST"; then
    log "Grandstream runtime V2 presente sha256=$sha"
    return 0
  fi
  [ "$sha" = "$GRANDSTREAM_STOCK_SHA256" ] || die "Grandstream.py baseline no soportado: $sha"
  log "Grandstream stock compatible sha256=$sha"
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
  for dst in     "$GRANDSTREAM_DST" "$AVAYA_DST" "$AVAYA_J129_TPL_DST" "$AVAYA_GLOBAL_TPL_DST" "$AVAYA_HTTP_DST"     "$MODULE/index.php" "$MODULE/libs/EndpointCredentialVault.class.php"     "$MODULE/dialogs/summary/index.php" "$MODULE/dialogs/summary/lang/en.lang"     "$MODULE/themes/default/reporte_endpoints.tpl" "$MODULE/themes/default/js/javascript.js"     "$CLI_DST"; do
    backup_one "$dst"
  done

  log 'BACKUP-PASS'
}

install_base_runtime(){
  local tmp
  if ! grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST"; then
    tmp="$(mktemp "$STATE_DIR/Grandstream.py.XXXXXX")"
    python3 -B "$PATCHER" "$GRANDSTREAM_DST" "$tmp"
    python3 -B -m py_compile "$tmp"
    grep -Fq "$GRANDSTREAM_V2_MARKER" "$tmp" || die 'Grandstream V2 target marker missing'
    install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_DST"
    rm -f "$tmp" "${GRANDSTREAM_DST}c" 2>/dev/null || true
  fi

  install -o root -g root -m 0644 "$AVAYA_SRC" "$AVAYA_DST"
  install -o root -g root -m 0644 "$AVAYA_J129_TPL_SRC" "$AVAYA_J129_TPL_DST"
  install -o root -g root -m 0644 "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_GLOBAL_TPL_DST"
  install -o root -g root -m 0644 "$AVAYA_HTTP_SRC" "$AVAYA_HTTP_DST"
  python3 -B -m py_compile "$AVAYA_DST"
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
  if [ "$tables" = 0 ]; then
    mysql --defaults-extra-file="$df" endpointconfig < "$SCHEMA_SQL"
    log 'CREDENTIAL-SCHEMA-INSTALL-PASS'
  fi
  verify_schema "$df"
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
  grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST" || die 'Grandstream V2 runtime missing'
  python3 -B -m py_compile "$GRANDSTREAM_DST"
  python3 -B -m py_compile "$AVAYA_DST"

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
  trap 'rc=$?; if [ "$installing" -eq 1 ]; then echo "[Endpoint Configuration 1.0.1-rc2] install failed; runtime backup remains available" >&2; fi; exit "$rc"' ERR

  install_base_runtime
  install_catalog
  install_credentials
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
  [ -f "$MANIFEST" ] || die 'no existe manifest RC2 de backup'
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

RC2 instala el runtime completo validado en Ceiba:
- Grandstream V2
- Avaya J129
- Extension / Registration
- seguridad administrativa y vault cifrado

NO ejecuta discovery, NO asigna extensiones y NO configura/reinicia teléfonos.
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
