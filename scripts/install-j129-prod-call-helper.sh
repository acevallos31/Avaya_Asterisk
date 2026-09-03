#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/acevallos31/Avaya_Asterisk/Audit/deploy/j129"
HELPER_NAME="avaya-j129-prod-call-test"
SUDOERS_NAME="avaya-j129-prod-call-test.sudoers"
TMPDIR="$(mktemp -d /tmp/j129-call-helper.XXXXXX)"

cleanup(){ rm -rf "$TMPDIR"; }
trap cleanup EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }

[ "${EUID}" -eq 0 ] || fail "ejecutar como root"
command -v curl >/dev/null 2>&1 || fail "curl no está instalado"
command -v install >/dev/null 2>&1 || fail "install no está disponible"
command -v visudo >/dev/null 2>&1 || fail "visudo no está disponible"

curl -fsSL "$BASE_URL/$HELPER_NAME" -o "$TMPDIR/$HELPER_NAME"
curl -fsSL "$BASE_URL/$SUDOERS_NAME" -o "$TMPDIR/$SUDOERS_NAME"

test -s "$TMPDIR/$HELPER_NAME" || fail "helper descargado vacío"
test -s "$TMPDIR/$SUDOERS_NAME" || fail "sudoers descargado vacío"
bash -n "$TMPDIR/$HELPER_NAME" || fail "helper tiene error de sintaxis"
visudo -cf "$TMPDIR/$SUDOERS_NAME" >/dev/null || fail "sudoers inválido"

install -o root -g root -m 0755 "$TMPDIR/$HELPER_NAME" \
  "/usr/local/sbin/$HELPER_NAME"
install -o root -g root -m 0440 "$TMPDIR/$SUDOERS_NAME" \
  "/etc/sudoers.d/avaya-j129-prod-call-test"

visudo -cf /etc/sudoers.d/avaya-j129-prod-call-test

echo
ls -l /usr/local/sbin/avaya-j129-prod-call-test
ls -l /etc/sudoers.d/avaya-j129-prod-call-test

echo
echo "J129-PROD-CALL-HELPER-INSTALL-PASS"
