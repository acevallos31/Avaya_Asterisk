#!/usr/bin/env bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/acevallos31/Avaya_Asterisk/Audit"
HELPER_URL="$REPO_RAW/deploy/j129/avaya-j129-lab-call-test"
SUDOERS_URL="$REPO_RAW/deploy/j129/avaya-j129-lab-call-test.sudoers"
HELPER_DST="/usr/local/sbin/avaya-j129-lab-call-test"
SUDOERS_DST="/etc/sudoers.d/avaya-j129-lab-call-test"

[ "$(id -u)" -eq 0 ] || { echo 'ERROR: ejecutar como root' >&2; exit 1; }
for cmd in curl install visudo bash; do command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: falta $cmd" >&2; exit 1; }; done

tmpdir="$(mktemp -d /tmp/j129-lab-call-install.XXXXXX)"
trap 'rm -rf "$tmpdir"' EXIT
curl -fsSL "$HELPER_URL" -o "$tmpdir/helper"
curl -fsSL "$SUDOERS_URL" -o "$tmpdir/sudoers"
[ -s "$tmpdir/helper" ] && [ -s "$tmpdir/sudoers" ] || { echo 'ERROR: descarga vacía' >&2; exit 1; }
bash -n "$tmpdir/helper"
visudo -cf "$tmpdir/sudoers"
install -o root -g root -m 0755 "$tmpdir/helper" "$HELPER_DST"
install -o root -g root -m 0440 "$tmpdir/sudoers" "$SUDOERS_DST"
visudo -cf "$SUDOERS_DST"
stat -c '%n %U:%G %a' "$HELPER_DST" "$SUDOERS_DST"
echo 'J129-LAB-CALL-HELPER-INSTALL-PASS'
