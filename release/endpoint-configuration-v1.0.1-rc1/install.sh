#!/usr/bin/env bash
set -euo pipefail
umask 077
export PYTHONDONTWRITEBYTECODE=1

VERSION='1.0.1-rc1'
NAME='issabel-endpoint-configuration'
STATE_DIR="/var/lib/${NAME}/${VERSION}"
BACKUP_DIR="${STATE_DIR}/backup"
MANIFEST="${STATE_DIR}/runtime.manifest"
INSTALLED="${STATE_DIR}/installed.version"

AMPORTAL_CONF='/etc/amportal.conf'
ENDPOINT_BASE='/usr/share/issabel/endpoint-classes'
GRANDSTREAM_DST="${ENDPOINT_BASE}/class/issabel/vendor/Grandstream.py"
AVAYA_DST="${ENDPOINT_BASE}/class/issabel/vendor/Avaya.py"
AVAYA_J129_TPL_DST="${ENDPOINT_BASE}/tpl/Avaya_J129.tpl"
AVAYA_GLOBAL_TPL_DST="${ENDPOINT_BASE}/tpl/Avaya_global_SIP.tpl"
AVAYA_HTTP_DST='/etc/httpd/conf.d/avaya-j129-provisioning.conf'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="${SCRIPT_DIR}/payload"
PATCHER="${PAYLOAD}/grandstream-vendor-patch.py"
CATALOG_SQL="${PAYLOAD}/grandstream-catalog.sql"
AVAYA_SRC="${PAYLOAD}/Avaya.py"
AVAYA_J129_TPL_SRC="${PAYLOAD}/Avaya_J129.tpl"
AVAYA_GLOBAL_TPL_SRC="${PAYLOAD}/Avaya_global_SIP.tpl"
AVAYA_HTTP_SRC="${PAYLOAD}/avaya-j129-provisioning.conf"

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
  f="$(mktemp /tmp/endpoint-config-db.XXXXXX.cnf)"; chmod 0600 "$f"
  {
    echo '[client]'
    printf 'user="%s"\n' "$(escape_mysql "$u")"
    printf 'password="%s"\n' "$(escape_mysql "$p")"
    printf 'host="%s"\n' "$(escape_mysql "$h")"
  } > "$f"
  printf '%s' "$f"
}
scalar(){ mysql --defaults-extra-file="$1" --batch --skip-column-names endpointconfig -e "$2"; }

check_payload(){
  for f in "$PATCHER" "$CATALOG_SQL" "$AVAYA_SRC" "$AVAYA_J129_TPL_SRC" "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_HTTP_SRC"; do
    need_file "$f"
  done
  python3 -B -m py_compile "$PATCHER"
  python3 -B -m py_compile "$AVAYA_SRC"
  grep -Fq 'CEIBA-GRANDSTREAM-PROD-V2-GXP16XX' "$PATCHER" || die 'patcher V2 marker missing'
}

check_grandstream_baseline(){
  local sha
  need_file "$GRANDSTREAM_DST"
  sha="$(sha256sum "$GRANDSTREAM_DST" | awk '{print $1}')"
  if grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST"; then
    log "Grandstream runtime ya está en V2 sha256=$sha"
    return 0
  fi
  [ "$sha" = "$GRANDSTREAM_STOCK_SHA256" ] || die "Grandstream.py baseline no soportado: $sha"
  log "Grandstream stock compatible sha256=$sha"
}

preflight(){
  need_root
  for cmd in python3 php mysql curl openssl apachectl install sha256sum mktemp; do
    command -v "$cmd" >/dev/null 2>&1 || die "comando requerido no disponible: $cmd"
  done
  [ -d "$ENDPOINT_BASE" ] || die 'Issabel Endpoint Configurator no encontrado'
  need_file /usr/bin/issabel-endpointconfig
  check_payload
  check_grandstream_baseline

  local df mf gxp conflicts avaya_conflicts
  df="$(make_defaults)"; trap 'rm -f "$df"' RETURN EXIT
  mf="$(scalar "$df" "SELECT COUNT(*) FROM manufacturer WHERE name='Grandstream';")"
  gxp="$(scalar "$df" "SELECT COUNT(*) FROM model m JOIN manufacturer f ON f.id=m.id_manufacturer WHERE f.name='Grandstream' AND m.name='GXP1625';")"
  conflicts="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix p LEFT JOIN manufacturer f ON f.id=p.id_manufacturer WHERE UPPER(p.mac_prefix) IN ('C0:74:AD','EC:74:D7') AND COALESCE(f.name,'')<>'Grandstream';")"
  avaya_conflicts="$(scalar "$df" "SELECT COUNT(*) FROM mac_prefix p LEFT JOIN manufacturer f ON f.id=p.id_manufacturer WHERE UPPER(p.mac_prefix)='C8:1F:EA' AND COALESCE(f.name,'')<>'Avaya';")"
  [ "$mf" = 1 ] || die "fabricante Grandstream esperado una vez, encontrado=$mf"
  [ "$gxp" = 1 ] || die "modelo base GXP1625 esperado una vez, encontrado=$gxp"
  [ "$conflicts" = 0 ] || die 'OUI Grandstream pertenece a otro fabricante'
  [ "$avaya_conflicts" = 0 ] || die 'OUI Avaya C8:1F:EA pertenece a otro fabricante'
  rm -f "$df"; trap - RETURN EXIT
  apachectl -t >/dev/null
  log 'PREFLIGHT-PASS'
  log 'phone_write=NO'
  log 'endpoint_discovery=NO'
}

backup_one(){
  local dst="$1" key="$2" rel
  rel="${dst#/}"
  if [ -e "$dst" ]; then
    install -d -m 0700 "$BACKUP_DIR/$(dirname "$rel")"
    cp -a "$dst" "$BACKUP_DIR/$rel"
    printf 'PRESENT %s %s\n' "$key" "$dst" >> "$MANIFEST"
  else
    printf 'ABSENT %s %s\n' "$key" "$dst" >> "$MANIFEST"
  fi
}

save_state(){
  [ ! -f "$MANIFEST" ] || return 0
  install -d -o root -g root -m 0700 "$STATE_DIR" "$BACKUP_DIR"
  : > "$MANIFEST"; chmod 0600 "$MANIFEST"
  backup_one "$GRANDSTREAM_DST" grandstream
  backup_one "$AVAYA_DST" avaya
  backup_one "$AVAYA_J129_TPL_DST" avaya_j129_tpl
  backup_one "$AVAYA_GLOBAL_TPL_DST" avaya_global_tpl
  backup_one "$AVAYA_HTTP_DST" avaya_http
  log 'BACKUP-PASS'
}

install_grandstream(){
  local tmp
  if grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST"; then
    log 'Grandstream V2 ya instalado; no se reemplaza'
    return 0
  fi
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.XXXXXX")"
  python3 -B "$PATCHER" "$GRANDSTREAM_DST" "$tmp"
  python3 -B -m py_compile "$tmp"
  grep -Fq "$GRANDSTREAM_V2_MARKER" "$tmp" || die 'target Grandstream V2 marker missing'
  grep -Fq "'Accept': '*/*'" "$tmp" || die 'target GXP16xx Accept header missing'
  grep -Fq "cookie_parts.append('session-identity=' + sid)" "$tmp" || die 'target GXP16xx session identity missing'
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_DST"
  rm -f "$tmp" "${GRANDSTREAM_DST}c" 2>/dev/null || true
}

install_avaya(){
  install -o root -g root -m 0644 "$AVAYA_SRC" "$AVAYA_DST"
  install -o root -g root -m 0644 "$AVAYA_J129_TPL_SRC" "$AVAYA_J129_TPL_DST"
  install -o root -g root -m 0644 "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_GLOBAL_TPL_DST"
  install -o root -g root -m 0644 "$AVAYA_HTTP_SRC" "$AVAYA_HTTP_DST"
  python3 -B -m py_compile "$AVAYA_DST"
  apachectl -t >/dev/null
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

verify(){
  need_root
  check_payload
  grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST" || die 'Grandstream V2 runtime missing'
  python3 -B -m py_compile "$GRANDSTREAM_DST"
  python3 -B -m py_compile "$AVAYA_DST"
  cmp -s "$AVAYA_SRC" "$AVAYA_DST" || die 'Avaya.py no coincide con payload validado'
  cmp -s "$AVAYA_J129_TPL_SRC" "$AVAYA_J129_TPL_DST" || die 'Avaya_J129.tpl no coincide'
  cmp -s "$AVAYA_GLOBAL_TPL_SRC" "$AVAYA_GLOBAL_TPL_DST" || die 'Avaya_global_SIP.tpl no coincide'
  cmp -s "$AVAYA_HTTP_SRC" "$AVAYA_HTTP_DST" || die 'Apache J129 config no coincide'
  apachectl -t >/dev/null

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
  log 'VERIFY-PASS'
  log 'supported_grandstream=GXP1625,GRP2601P,GRP2602G'
  log 'supported_avaya=J129'
  log 'phone_write=NO'
  log 'endpoint_discovery=NO'
}

install_all(){
  preflight
  save_state
  install_grandstream
  install_avaya
  install_catalog
  apachectl -t >/dev/null
  systemctl reload httpd
  printf '%s\n' "$VERSION" > "$INSTALLED"; chmod 0600 "$INSTALLED"
  verify
  log 'INSTALL-PASS'
  log 'IMPORTANTE: discovery, asignación de extensiones y Configure se ejecutan manualmente después.'
}

restore_from_manifest(){
  local state key dst rel
  [ -f "$MANIFEST" ] || die 'no existe manifest de backup'
  while read -r state key dst; do
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
  restore_from_manifest
  python3 -B -m py_compile "$GRANDSTREAM_DST"
  [ ! -f "$AVAYA_DST" ] || python3 -B -m py_compile "$AVAYA_DST"
  apachectl -t >/dev/null
  systemctl reload httpd
  rm -f "$INSTALLED"
  log 'ROLLBACK-RUNTIME-PASS'
  log 'catalog_rollback=NO_ADDITIVE_ROWS_RETAINED'
  log 'phone_write=NO'
}

status(){
  printf 'version=%s\n' "$VERSION"
  if [ -f "$INSTALLED" ]; then printf 'installed=YES\n'; else printf 'installed=NO\n'; fi
  if [ -f "$GRANDSTREAM_DST" ] && grep -Fq "$GRANDSTREAM_V2_MARKER" "$GRANDSTREAM_DST"; then
    printf 'grandstream_v2=YES\n'
  else
    printf 'grandstream_v2=NO\n'
  fi
}

usage(){
  cat <<'EOF'
Uso:
  sudo ./install.sh preflight
  sudo ./install.sh install
  sudo ./install.sh verify
  sudo ./install.sh rollback
  ./install.sh status

El instalador NO ejecuta discovery, NO asigna extensiones y NO configura/reinicia teléfonos.
EOF
}

case "${1:-}" in
  preflight) preflight ;;
  install) install_all ;;
  verify) verify ;;
  rollback) rollback ;;
  status) status ;;
  -h|--help|help|'') usage ;;
  *) usage; exit 2 ;;
esac
