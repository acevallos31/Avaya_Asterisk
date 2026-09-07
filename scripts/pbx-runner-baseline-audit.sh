#!/usr/bin/env bash
set -euo pipefail

TARGET="${TARGET:-unknown}"
EXPECTED_USER="${EXPECTED_USER:-}"
EXPECTED_HOST="${EXPECTED_HOST:-}"

if [[ -n "$EXPECTED_USER" ]]; then
  test "$(id -un)" = "$EXPECTED_USER"
fi
if [[ -n "$EXPECTED_HOST" ]]; then
  test "$(hostname -s)" = "$EXPECTED_HOST"
fi

echo "=== TARGET ==="
echo "target=$TARGET"

echo '=== HOST ==='
echo "hostname_fqdn=$(hostname -f 2>/dev/null || hostname)"
echo "hostname_short=$(hostname -s 2>/dev/null || hostname)"
echo "kernel=$(uname -srmo)"
echo "uptime=$(uptime -p 2>/dev/null || true)"

echo '=== RUNNER ==='
echo "user=$(id -un)"
echo "uid=$(id -u)"
echo "groups=$(id -Gn)"
echo "runner_name=${RUNNER_NAME:-unknown}"
echo "runner_os=${RUNNER_OS:-unknown}"
echo "runner_arch=${RUNNER_ARCH:-unknown}"

echo '=== OS RELEASE ==='
cat /etc/os-release 2>/dev/null || true

echo '=== CPU ==='
lscpu 2>/dev/null | grep -E '^(Architecture|CPU\(s\)|Model name|Virtualization):' || true

echo '=== MEMORY ==='
free -h || true

echo '=== FILESYSTEM ==='
df -hT / /var /tmp 2>/dev/null || df -hT || true

echo '=== ADDRESSES ==='
ip -br addr || true

echo '=== ROUTES ==='
ip route || true

echo '=== NEIGHBORS ==='
ip neigh show || true

echo '=== DNS ==='
grep -Ev '^\s*(#|$)' /etc/resolv.conf 2>/dev/null || true

echo '=== LISTENING PORTS (NO PIDS) ==='
ss -lntupH 2>/dev/null | awk '{print $1,$5}' | sort -u | head -n 200 || true

echo '=== ISSABEL PACKAGES ==='
rpm -qa 2>/dev/null | grep -Ei '^(issabel|asterisk|freepbx|httpd|mariadb|mysql|php)' | sort | head -n 300 || true

echo '=== ASTERISK VERSION ==='
asterisk -V 2>/dev/null || true

echo '=== ENDPOINT CONFIGURATOR ==='
rpm -q issabel-endpointconfig2 2>/dev/null || true

echo '=== RUNTIME TOOLS ==='
for cmd in python3 python php mysql mariadb curl wget nmap arp arp-scan git openssl jq; do
  printf '%-12s ' "$cmd"
  command -v "$cmd" 2>/dev/null || echo 'NOT-INSTALLED'
done
python3 --version 2>/dev/null || true
php -v 2>/dev/null | head -n 2 || true
mysql --version 2>/dev/null || mariadb --version 2>/dev/null || true
git --version 2>/dev/null || true

echo '=== SERVICES ==='
for svc in asterisk httpd mariadb mysqld fail2ban firewalld chronyd crond; do
  if systemctl list-unit-files "$svc.service" >/dev/null 2>&1; then
    printf '%-12s enabled=' "$svc"; systemctl is-enabled "$svc" 2>/dev/null || true
    printf '%-12s active=' "$svc"; systemctl is-active "$svc" 2>/dev/null || true
  fi
done

echo '=== FAILED UNITS ==='
systemctl --failed --no-pager 2>/dev/null || true

echo '=== ASTERISK CLI READ-ONLY ==='
if asterisk -rx 'core show version' >/tmp/audit-asterisk-version.txt 2>/dev/null; then
  cat /tmp/audit-asterisk-version.txt
  asterisk -rx 'core show uptime' 2>/dev/null || true
  asterisk -rx 'module show like chan_sip' 2>/dev/null || true
  asterisk -rx 'module show like res_pjsip' 2>/dev/null || true
else
  echo 'WARN: runner sin acceso directo al CLI de Asterisk; no se amplían privilegios.'
fi
rm -f /tmp/audit-asterisk-version.txt

echo '=== ENDPOINT CLASSES ==='
base='/usr/share/issabel/endpoint-classes/class/issabel/vendor'
[ -d "$base" ] && find "$base" -maxdepth 1 -type f -name '*.py' -printf '%f\n' | sort || true

echo '=== LEGACY PHONE SERVER VENDORS ==='
legacy='/var/www/html/modules/endpoint_configurator/phonesrv/vendor'
[ -d "$legacy" ] && find "$legacy" -maxdepth 1 -type f -name '*.class.php' -printf '%f\n' | sort || true

echo '=== DETECTION COMPONENTS ==='
for f in /usr/bin/issabel-endpointconfig /usr/bin/detect_endpoints /usr/sbin/detect_endpoints /usr/share/issabel/privileged/detect_endpoints; do
  [ -e "$f" ] && ls -l "$f"
done

echo '=== ENVIRONMENT-SPECIFIC READ-ONLY HELPER ==='
case "$TARGET" in
  lab)
    if [ -x /usr/local/sbin/avaya-j129-lab-deploy ] && sudo -n -l 2>/dev/null | grep -Fq '/usr/local/sbin/avaya-j129-lab-deploy'; then
      sudo /usr/local/sbin/avaya-j129-lab-deploy inspect-db || true
    fi
    ;;
  ceiba-production)
    if sudo -n -l 2>/dev/null | grep -Fq '/usr/local/sbin/avaya-j129-prod-validation'; then
      sudo -n /usr/local/sbin/avaya-j129-prod-validation audit '' || true
    fi
    ;;
esac

echo '=== SUDO ALLOWLIST ==='
sudo -n -l 2>&1 | sed -E 's/(password|passwd|secret|token|key)[^, ]*/[REDACTED]/Ig' || true

echo '=== DISCOVERY TOOLING ==='
for cmd in nmap arp-scan arp ip ss curl; do
  command -v "$cmd" >/dev/null 2>&1 && echo "PASS: $cmd" || echo "WARN: $cmd no instalado"
done

echo '=== LOCAL HTTP HEALTH ==='
curl -kfsS --max-time 5 -o /dev/null -w 'http://127.0.0.1 status=%{http_code}\n' http://127.0.0.1/ 2>/dev/null || echo 'WARN: HTTP local no respondió'
curl -kfsS --max-time 5 -o /dev/null -w 'https://127.0.0.1 status=%{http_code}\n' https://127.0.0.1/ 2>/dev/null || echo 'WARN: HTTPS local no respondió'

echo '=== BASELINE SUMMARY ==='
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "target=$TARGET"
echo "host=$(hostname -f 2>/dev/null || hostname)"
echo "runner_user=$(id -un)"
echo "endpointconfig=$(rpm -q issabel-endpointconfig2 2>/dev/null || echo NOT-INSTALLED)"
echo "asterisk=$(asterisk -V 2>/dev/null || echo UNKNOWN)"
echo 'BASELINE-STATUS: PASS-WITH-WARNINGS-IF-ANY'
echo 'PBX-RUNNER-BASELINE-AUDIT-PASS'
