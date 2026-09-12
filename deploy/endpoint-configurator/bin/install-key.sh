#!/usr/bin/env bash
set -euo pipefail
umask 077

KEY_FILE="${1:-/etc/issabel/endpoint-configurator.key}"
KEY_DIR="$(dirname "$KEY_FILE")"

install -d -m 0750 -o root -g apache "$KEY_DIR"
if [[ -e "$KEY_FILE" ]]; then
  [[ -f "$KEY_FILE" ]] || { echo "ERROR: key path is not a regular file" >&2; exit 2; }
  [[ "$(stat -c '%a' "$KEY_FILE")" == "600" ]] || { echo "ERROR: existing key permissions must be 600" >&2; exit 3; }
  exit 0
fi

tmp="$(mktemp "${KEY_FILE}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
openssl rand 32 > "$tmp"
chown root:apache "$tmp"
chmod 0600 "$tmp"
mv -f "$tmp" "$KEY_FILE"
trap - EXIT
