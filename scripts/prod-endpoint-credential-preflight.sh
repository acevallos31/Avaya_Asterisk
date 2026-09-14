#!/usr/bin/env bash
set -euo pipefail
umask 077

EXPECTED_USER='github-runner-prod'
EXPECTED_HOST='cei-pbx02'
PROD_HELPER='/usr/local/sbin/avaya-j129-prod-validation'
MODULE='/var/www/html/modules/endpoint_configurator'
REPORT="${REPORT:-/tmp/test70-endpoint-credential-preflight.txt}"

# Git blob SHAs from the exact Audit baseline commit
# ce90056c652c7e3a280fc8a1416580e6172dcc01.
EXPECTED_INDEX_BLOB='b68103a3c28265b3ef2619f663b0f6ed87ffa89f'
EXPECTED_TEMPLATE_BLOB='d979762079d4dcc2874759881104b3287fea71c2'
EXPECTED_JS_BLOB='44bea8adac8bd15d9b8548922d032fcf924edfc1'

fail() {
  printf 'TEST70-FAIL: %s\n' "$*" | tee -a "$REPORT" >&2
  exit 1
}

record() {
  printf '%s\n' "$*" | tee -a "$REPORT"
}

check_live_blob() {
  local relative="$1" expected="$2" live actual
  live="$MODULE/$relative"
  [ -f "$live" ] || fail "live file missing: $relative"
  actual="$(git hash-object "$live")"
  if [ "$actual" != "$expected" ]; then
    record "TEST70-DRIFT-BLOCK path=$relative expected_blob=$expected actual_blob=$actual"
    exit 1
  fi
  record "TEST70-DRIFT-PASS path=$relative blob=$actual"
}

: > "$REPORT"
chmod 0600 "$REPORT"

[ "$(id -un)" = "$EXPECTED_USER" ] || fail 'unexpected runner user'
[ "$(hostname -s)" = "$EXPECTED_HOST" ] || fail 'unexpected production host'
command -v git >/dev/null 2>&1 || fail 'git is required for immutable blob comparison'
command -v curl >/dev/null 2>&1 || fail 'curl is required for local web health'
[ -x "$PROD_HELPER" ] || fail 'production validation helper missing'
[ "$(stat -c '%U:%G:%a' "$PROD_HELPER")" = 'root:root:755' ] || fail 'production helper ownership/mode mismatch'
sudo -n -l 2>&1 | grep -F "$PROD_HELPER" >/dev/null || fail 'production helper is not allowlisted for runner'

record 'TEST70-PROD-RUNNER-GUARD-PASS'
record "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
record "host=$(hostname -s)"
record "runner_user=$(id -un)"
record 'baseline_commit=ce90056c652c7e3a280fc8a1416580e6172dcc01'

# Do not print file contents. A mismatch is a hard stop before any deployment.
check_live_blob 'index.php' "$EXPECTED_INDEX_BLOB"
check_live_blob 'themes/default/reporte_endpoints.tpl' "$EXPECTED_TEMPLATE_BLOB"
check_live_blob 'themes/default/js/javascript.js' "$EXPECTED_JS_BLOB"
record 'TEST70-PROD-ENDPOINT-BASELINE-PASS'

# Existing root-owned helper; fleet-audit is read-only and sanitizes credentials.
fleet_tmp="$(mktemp /tmp/test70-fleet.XXXXXX)"
trap 'rm -f "$fleet_tmp"' EXIT
sudo -n "$PROD_HELPER" fleet-audit | tee "$fleet_tmp"
grep -F 'J129-PROD-FLEET-AUDIT-PASS' "$fleet_tmp" >/dev/null || fail 'production fleet audit did not pass'
cat "$fleet_tmp" >> "$REPORT"
rm -f "$fleet_tmp"
trap - EXIT

https_status="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 8 https://127.0.0.1/ || true)"
if [ "$https_status" = '000' ] || [ "$https_status" -lt 200 ] 2>/dev/null || [ "$https_status" -ge 500 ] 2>/dev/null; then
  fail "local Issabel HTTPS health failed: status=${https_status:-000}"
fi
record "local_https_status=$https_status"
record 'TEST70-PROD-WEB-HEALTH-PASS'

# Candidate-only paths are inventory information. This script never creates,
# changes or removes them.
for path in \
  /etc/issabel/endpoint-configurator.key \
  /var/www/html/modules/endpoint_configurator/libs/EndpointCredentialVault.class.php \
  /var/www/html/modules/endpoint_configurator/dialogs/summary/index.php \
  /var/www/html/modules/endpoint_configurator/dialogs/summary/lang/en.lang \
  /usr/local/libexec/issabel-endpoint-credential-vault; do
  if [ -e "$path" ]; then
    record "candidate_runtime_path=PRESENT path=$path"
  else
    record "candidate_runtime_path=ABSENT path=$path"
  fi
done

record 'production_runtime_write=NO'
record 'endpointconfig_write=NO'
record 'phone_write=NO'
record 'TEST70-PROD-ENDPOINT-CREDENTIAL-PREFLIGHT=PASS'
