#!/usr/bin/env bash
set -euo pipefail

PREFIX="${1:-C0:74:AD}"
MODEL="${2:-GXP1625}"
REPORT="${3:-${RUNNER_TEMP:-/tmp}/grandstream-db-oui-audit.txt}"
PREFIX_NORM="$(printf '%s' "$PREFIX" | tr '[:lower:]' '[:upper:]')"
MODEL_NORM="$(printf '%s' "$MODEL" | tr -d ' ' | tr '[:lower:]' '[:upper:]')"

: > "$REPORT"
exec > >(tee -a "$REPORT") 2>&1

echo '=== GRANDSTREAM DB & OUI AUDIT (SOLO LECTURA) ==='
echo "prefix=$PREFIX_NORM"
echo "model=$MODEL_NORM"
echo "runner=$(id -un)@$(hostname -s)"
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo '=== AUTHORIZED DB HELPER ==='
if [ -x /usr/local/sbin/avaya-j129-lab-deploy ]; then
  echo 'helper=present'
else
  echo 'helper=missing'
fi
if sudo -n -l 2>/dev/null | grep -Fq '/usr/local/sbin/avaya-j129-lab-deploy'; then
  echo 'helper_sudo=authorized'
  echo '=== EXISTING HELPER BASELINE ==='
  sudo -n /usr/local/sbin/avaya-j129-lab-deploy inspect-db || true
else
  echo 'helper_sudo=not-authorized'
fi

echo '=== LIVE GRANDSTREAM DB QUERY ==='
if [ -r /etc/amportal.conf ] && command -v mysql >/dev/null 2>&1; then
  DBUSER="$(sed -n 's/^AMPDBUSER=//p' /etc/amportal.conf | head -n1)"
  DBPASS="$(sed -n 's/^AMPDBPASS=//p' /etc/amportal.conf | head -n1)"
  DBHOST="$(sed -n 's/^AMPDBHOST=//p' /etc/amportal.conf | head -n1)"
  [ -n "$DBHOST" ] || DBHOST=localhost
  CNF="$(mktemp "${RUNNER_TEMP:-/tmp}/grandstream-db.XXXXXX.cnf")"
  trap 'rm -f "$CNF"' EXIT
  chmod 600 "$CNF"
  {
    echo '[client]'
    printf 'user=%s\n' "$DBUSER"
    printf 'password=%s\n' "$DBPASS"
    printf 'host=%s\n' "$DBHOST"
  } > "$CNF"

  mysql --defaults-extra-file="$CNF" --batch --raw endpointconfig <<SQL
SET SESSION TRANSACTION READ ONLY;
SELECT '=== GRANDSTREAM MANUFACTURER ===';
SELECT id,name,description FROM manufacturer WHERE name='Grandstream';
SELECT '=== GRANDSTREAM MODEL ===';
SELECT m.id,m.id_manufacturer,m.name,m.description,m.max_accounts,m.static_ip_supported,m.dynamic_ip_supported,m.static_prov_supported
FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer
WHERE mf.name='Grandstream' AND UPPER(REPLACE(m.name,' ',''))='${MODEL_NORM}';
SELECT '=== GRANDSTREAM MODEL PROPERTIES ===';
SELECT mp.id,mp.property_key,CASE WHEN LOWER(mp.property_key) LIKE '%password%' THEN '***OCULTO***' ELSE mp.property_value END AS property_value
FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer
WHERE mf.name='Grandstream' AND UPPER(REPLACE(m.name,' ',''))='${MODEL_NORM}'
ORDER BY mp.property_key,mp.id;
SELECT '=== ALL GRANDSTREAM MAC PREFIXES ===';
SELECT mp.id,mp.id_manufacturer,mp.mac_prefix,mp.description,mf.name AS manufacturer
FROM mac_prefix mp JOIN manufacturer mf ON mf.id=mp.id_manufacturer
WHERE mf.name='Grandstream' ORDER BY mp.mac_prefix;
SELECT '=== REQUESTED PREFIX LOOKUP ===';
SELECT mp.id,mp.id_manufacturer,mp.mac_prefix,mp.description,mf.name AS manufacturer
FROM mac_prefix mp LEFT JOIN manufacturer mf ON mf.id=mp.id_manufacturer
WHERE UPPER(mp.mac_prefix)='${PREFIX_NORM}';
ROLLBACK;
SQL
  echo 'LIVE-GRANDSTREAM-DB-QUERY-PASS'
else
  echo 'LIVE-GRANDSTREAM-DB-QUERY=UNAVAILABLE'
fi

echo '=== STOCK SQL EVIDENCE ==='
for root in \
  /usr/share/issabel/module_installer/issabel-endpointconfig2-5.0.0-1.el8/setup/db \
  usr/share/issabel/module_installer/issabel-endpointconfig2-5.0.0-1.el8/setup/db; do
  [ -d "$root" ] || continue
  echo "--- root=$root ---"
  grep -RniF 'Grandstream' "$root" 2>/dev/null | head -n 120 || true
  echo "--- model=$MODEL_NORM ---"
  grep -RniF "$MODEL_NORM" "$root" 2>/dev/null | head -n 80 || true
  echo "--- prefix=$PREFIX_NORM ---"
  grep -RniFi "$PREFIX_NORM" "$root" 2>/dev/null | head -n 80 || true
done

echo 'GRANDSTREAM-DB-OUI-AUDIT-COMPLETE'
