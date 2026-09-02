#!/usr/bin/env bash
set -euo pipefail

# Auditoría READ-ONLY para una central Issabel candidata a Avaya J129 v0.1.0.
# No instala, no modifica DB, no recarga servicios y no imprime credenciales.

EXPECTED_RELEASE_SHA='74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3'
AMPORTAL_CONF='/etc/amportal.conf'
ENDPOINT_BASE='/usr/share/issabel/endpoint-classes'
ENDPOINT_BIN='/usr/bin/issabel-endpointconfig'
TARGET_OUI='C8:1F:EA'

pass(){ printf 'PASS  %s\n' "$*"; }
warn(){ printf 'WARN  %s\n' "$*"; }
fail(){ printf 'FAIL  %s\n' "$*"; FAILURES=$((FAILURES+1)); }
info(){ printf 'INFO  %s\n' "$*"; }

FAILURES=0

printf '%s\n' '=== J129 PRODUCTION READ-ONLY AUDIT v0.1.0 ==='
printf 'Expected release SHA: %s\n' "$EXPECTED_RELEASE_SHA"
printf 'Host: %s\n' "$(hostname -f 2>/dev/null || hostname)"
printf 'User: %s\n' "$(id -un)"
printf 'UTC: %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
printf '\n'

# Sistema / versiones
if [ -r /etc/redhat-release ]; then
  info "OS=$(cat /etc/redhat-release)"
else
  warn '/etc/redhat-release no disponible'
fi

if command -v asterisk >/dev/null 2>&1; then
  ASTERISK_VERSION="$(asterisk -rx 'core show version' 2>/dev/null | head -n1 || true)"
  [ -n "$ASTERISK_VERSION" ] && info "$ASTERISK_VERSION" || fail 'Asterisk CLI no respondió'
else
  fail 'asterisk no está en PATH'
fi

if command -v python3 >/dev/null 2>&1; then
  info "$(python3 --version 2>&1)"
else
  fail 'python3 no disponible'
fi

if command -v httpd >/dev/null 2>&1; then
  info "$(httpd -v 2>/dev/null | head -n1 || true)"
else
  fail 'httpd no disponible'
fi

if command -v apachectl >/dev/null 2>&1; then
  if apachectl -t >/tmp/j129-audit-apache.$$ 2>&1; then
    pass 'Apache Syntax OK'
  else
    fail 'apachectl -t falló'
    sed 's/^/APACHE  /' /tmp/j129-audit-apache.$$ || true
  fi
  rm -f /tmp/j129-audit-apache.$$
else
  fail 'apachectl no disponible'
fi

[ -d "$ENDPOINT_BASE" ] && pass "$ENDPOINT_BASE presente" || fail "$ENDPOINT_BASE ausente"
[ -f "$ENDPOINT_BIN" ] && pass "$ENDPOINT_BIN presente" || fail "$ENDPOINT_BIN ausente"

# MySQL/MariaDB sin exponer credenciales.
if ! command -v mysql >/dev/null 2>&1; then
  fail 'cliente mysql no disponible'
elif [ ! -r "$AMPORTAL_CONF" ]; then
  fail "$AMPORTAL_CONF no legible"
else
  read_amp(){ sed -n "s/^$1=//p" "$AMPORTAL_CONF" | head -n1; }
  escape_mysql(){ local v="$1"; v="${v//\\/\\\\}"; v="${v//\"/\\\"}"; printf '%s' "$v"; }

  DBUSER="$(read_amp AMPDBUSER)"
  DBPASS="$(read_amp AMPDBPASS)"
  DBHOST="$(read_amp AMPDBHOST)"
  [ -n "$DBHOST" ] || DBHOST='localhost'

  if [ -z "$DBUSER" ] || [ -z "$DBPASS" ]; then
    fail 'AMPDBUSER/AMPDBPASS no definidos en amportal.conf'
  else
    DF="$(mktemp /tmp/j129-prod-audit-db.XXXXXX.cnf)"
    chmod 0600 "$DF"
    trap 'rm -f "$DF"' EXIT
    {
      echo '[client]'
      printf 'user="%s"\n' "$(escape_mysql "$DBUSER")"
      printf 'password="%s"\n' "$(escape_mysql "$DBPASS")"
      printf 'host="%s"\n' "$(escape_mysql "$DBHOST")"
    } > "$DF"

    scalar(){ mysql --defaults-extra-file="$DF" --batch --skip-column-names endpointconfig -e "$1" 2>/dev/null; }

    if mysql --defaults-extra-file="$DF" --batch --skip-column-names -e 'SELECT 1;' >/dev/null 2>&1; then
      pass 'MySQL/MariaDB accesible con configuración Issabel'
    else
      fail 'No se pudo conectar a MySQL/MariaDB con configuración Issabel'
    fi

    if mysql --defaults-extra-file="$DF" --batch --skip-column-names -e "SHOW DATABASES LIKE 'endpointconfig';" 2>/dev/null | grep -qx endpointconfig; then
      pass 'DB endpointconfig presente'

      MF_COUNT="$(scalar "SELECT COUNT(*) FROM manufacturer WHERE name='Avaya';" || echo ERROR)"
      MODEL_COUNT="$(scalar "SELECT COUNT(*) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';" || echo ERROR)"
      OUI_CONFLICT="$(scalar "SELECT COUNT(*) FROM mac_prefix mp LEFT JOIN manufacturer mf ON mf.id=mp.id_manufacturer WHERE mp.mac_prefix='${TARGET_OUI}' AND COALESCE(mf.name,'')<>'Avaya';" || echo ERROR)"
      OUI_AVAYA="$(scalar "SELECT COUNT(*) FROM mac_prefix mp JOIN manufacturer mf ON mf.id=mp.id_manufacturer WHERE mp.mac_prefix='${TARGET_OUI}' AND mf.name='Avaya';" || echo ERROR)"
      MULTI="$(scalar "SELECT COUNT(*) FROM (SELECT ea.id_endpoint FROM endpoint_account ea JOIN endpoint e ON e.id=ea.id_endpoint JOIN manufacturer mf ON mf.id=e.id_manufacturer LEFT JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' GROUP BY ea.id_endpoint HAVING COUNT(*)>1) q;" || echo ERROR)"
      AVAYA_ENDPOINTS="$(scalar "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer WHERE mf.name='Avaya';" || echo ERROR)"

      for value_name in MF_COUNT MODEL_COUNT OUI_CONFLICT OUI_AVAYA MULTI AVAYA_ENDPOINTS; do
        eval "value=\${$value_name}"
        if [ "$value" = ERROR ]; then
          fail "Consulta DB falló: $value_name"
        fi
      done

      [ "$MF_COUNT" != ERROR ] && {
        [ "$MF_COUNT" -le 1 ] && pass "Fabricante Avaya sin duplicados (count=$MF_COUNT)" || fail "Fabricante Avaya duplicado (count=$MF_COUNT)"
      }
      [ "$MODEL_COUNT" != ERROR ] && {
        [ "$MODEL_COUNT" -le 1 ] && pass "Modelo J129 sin duplicados (count=$MODEL_COUNT)" || fail "Modelo J129 duplicado (count=$MODEL_COUNT)"
      }
      [ "$OUI_CONFLICT" != ERROR ] && {
        [ "$OUI_CONFLICT" -eq 0 ] && pass "OUI $TARGET_OUI sin conflicto" || fail "OUI $TARGET_OUI asignado a otro fabricante"
      }
      [ "$OUI_AVAYA" != ERROR ] && info "OUI $TARGET_OUI ya asociado a Avaya: count=$OUI_AVAYA"
      [ "$MULTI" != ERROR ] && {
        [ "$MULTI" -eq 0 ] && pass 'No hay J129 con más de una cuenta' || fail "Hay J129 multicuenta incompatibles con v0.1.0 (count=$MULTI)"
      }
      [ "$AVAYA_ENDPOINTS" != ERROR ] && info "Endpoints Avaya existentes: $AVAYA_ENDPOINTS"
    else
      fail 'DB endpointconfig no encontrada'
    fi

    rm -f "$DF"
    trap - EXIT
  fi
fi

printf '\n=== RESULTADO ===\n'
if [ "$FAILURES" -eq 0 ]; then
  echo 'J129-PRODUCTION-AUDIT-PASS'
  echo 'DECISION=APTO-PARA-PREFLIGHT-DE-RELEASE'
  exit 0
fi

echo "J129-PRODUCTION-AUDIT-FAIL failures=$FAILURES"
echo 'DECISION=NO-INSTALAR'
exit 1
