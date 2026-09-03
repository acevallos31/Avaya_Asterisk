#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/acevallos31/Avaya_Asterisk"
RUNNER_VERSION="2.337.0"
RUNNER_USER="github-runner-prod"
RUNNER_HOME="/opt/actions-runner-prod"
RUNNER_WORK="_work"
HOST_SHORT="$(hostname -s)"
RUNNER_NAME="${HOST_SHORT}-j129-production"
LABELS="j129-production,${HOST_SHORT}"
ARCHIVE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${ARCHIVE}"

fail(){ echo "ERROR: $*" >&2; exit 1; }

[ "${EUID}" -eq 0 ] || fail "ejecutar como root"
command -v curl >/dev/null 2>&1 || fail "curl no está instalado"
command -v tar >/dev/null 2>&1 || fail "tar no está instalado"
command -v systemctl >/dev/null 2>&1 || fail "systemd no está disponible"

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$RUNNER_USER"
fi

mkdir -p "$RUNNER_HOME"
chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME"

if [ -f "$RUNNER_HOME/.runner" ]; then
  echo "El runner ya está configurado en $RUNNER_HOME"
  echo "Runner esperado: $RUNNER_NAME"
  systemctl --no-pager --type=service --state=running | grep -F 'actions.runner.' || true
  echo "J129-PROD-RUNNER-ALREADY-CONFIGURED"
  exit 0
fi

TMP="$(mktemp -d /tmp/github-runner-prod.XXXXXX)"
cleanup(){
  unset RUNNER_TOKEN 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT

printf 'Token temporal de registro del self-hosted runner: '
IFS= read -r -s RUNNER_TOKEN
echo
[ -n "$RUNNER_TOKEN" ] || fail "token vacío"

curl -fL "$DOWNLOAD_URL" -o "$TMP/$ARCHIVE"
tar -xzf "$TMP/$ARCHIVE" -C "$RUNNER_HOME"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME"

if [ -x "$RUNNER_HOME/bin/installdependencies.sh" ]; then
  "$RUNNER_HOME/bin/installdependencies.sh"
fi

runuser -u "$RUNNER_USER" -- bash -c '
  set -euo pipefail
  cd "$1"
  ./config.sh \
    --unattended \
    --url "$2" \
    --token "$3" \
    --name "$4" \
    --labels "$5" \
    --work "$6"
' bash "$RUNNER_HOME" "$REPO_URL" "$RUNNER_TOKEN" "$RUNNER_NAME" "$LABELS" "$RUNNER_WORK"

unset RUNNER_TOKEN

cd "$RUNNER_HOME"
./svc.sh install "$RUNNER_USER"
./svc.sh start

sleep 2
./svc.sh status || true

echo
echo "Repo:    $REPO_URL"
echo "Runner:  $RUNNER_NAME"
echo "Usuario: $RUNNER_USER"
echo "Ruta:    $RUNNER_HOME"
echo "Labels:  self-hosted, Linux, X64, $LABELS"
echo
echo "J129-PROD-RUNNER-INSTALL-PASS"
