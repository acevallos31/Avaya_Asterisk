#!/usr/bin/env python3
"""Inject the reversible G10-15 Grandstream Host/Referer actions into the authorized LAB helper source.

This edits only the checked-out helper source. The workflow then validates it and
uses the existing privileged helper-sync mechanism to install the authorized
helper path on the LAB runner.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare-g10-15-helper.py <helper-path>")

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

if "GRANDSTREAM_HEADERS_PATCH_BACKUP=" not in text:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    repl = anchor + 'GRANDSTREAM_HEADERS_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-15"\n'
    if text.count(anchor) != 1:
        raise SystemExit("G10-15: backup variable anchor not found exactly once")
    text = text.replace(anchor, repl, 1)

funcs = r'''
inspect_grandstream_headers_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  local username_count host_count referer_count file_sha
  username_count="$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  file_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  echo '=== GRANDSTREAM GXP16xx HOST-REFERER PATCH AUDIT ==='
  echo "grandstream_py_sha256=$file_sha"
  echo "username_payload_line_count=$username_count"
  echo "host_header_line_count=$host_count"
  echo "referer_header_line_count=$referer_count"
  if [ -f "$GRANDSTREAM_HEADERS_PATCH_BACKUP" ]; then
    echo 'g10_15_backup_present=YES'
    echo "g10_15_backup_sha256=$(sha256sum "$GRANDSTREAM_HEADERS_PATCH_BACKUP" | awk '{print $1}')"
  else
    echo 'g10_15_backup_present=NO'
  fi
  if [ "$username_count" -eq 1 ] && [ "$host_count" -eq 0 ] && [ "$referer_count" -eq 0 ]; then
    echo 'headers_patch_state=READY'
  elif [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ]; then
    echo 'headers_patch_state=PATCHED'
  else
    echo 'headers_patch_state=UNEXPECTED'
    exit 1
  fi
  echo 'GRANDSTREAM-HEADERS-PATCH-INSPECT-PASS'
}

apply_grandstream_headers_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  install -d -o root -g root -m 0700 "$STATE_DIR"
  local username_count host_count referer_count before_sha after_sha tmp
  username_count="$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  if [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ]; then
    echo 'GRANDSTREAM-HEADERS-PATCH-ALREADY-PRESENT'
    return 0
  fi
  [ "$username_count" -eq 1 ] && [ "$host_count" -eq 0 ] && [ "$referer_count" -eq 0 ] || { echo 'ERROR: G10-14 no está aplicado o el baseline es inesperado; apply cancelado.' >&2; exit 1; }
  [ ! -e "$GRANDSTREAM_HEADERS_PATCH_BACKUP" ] || { echo "ERROR: ya existe backup G10-15 pendiente: $GRANDSTREAM_HEADERS_PATCH_BACKUP" >&2; exit 1; }
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_HEADERS_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_HEADERS_PATCH_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.g10-15.XXXXXX")"
  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
old = """            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            # GXP16xx firmware requires both HTTP credential fields.
            payload = urlencode({
                'username': self._http_username,
                'password': self._http_password,
            })"""
new = """            # GXP16xx firmware requires credentials and a matching Host/Referer pair.
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': self._ip,
                'Referer': 'http://%s/' % self._ip,
            }
            payload = urlencode({
                'username': self._http_username,
                'password': self._http_password,
            })"""
if text.count(old) != 1:
    raise SystemExit('G10-15 expected exactly one G10-14 login block')
text = text.replace(old, new, 1)
open(dst, 'w', encoding='utf-8').write(text)
PY
  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: el SHA no cambió después de G10-15.' >&2; exit 1; }
  grep -Fq "                'Host': self._ip," "$GRANDSTREAM_PY"
  grep -Fq "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY"
  echo "before_sha256=$before_sha"
  echo "after_sha256=$after_sha"
  echo 'GRANDSTREAM-HEADERS-PATCH-APPLY-PASS'
}

rollback_grandstream_headers_patch() {
  [ -f "$GRANDSTREAM_HEADERS_PATCH_BACKUP" ] || { echo 'ERROR: no existe backup controlado G10-15.' >&2; exit 1; }
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  local host_count referer_count restored_sha
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] || { echo 'ERROR: el live file no contiene G10-15; rollback cancelado.' >&2; exit 1; }
  python3 -m py_compile "$GRANDSTREAM_HEADERS_PATCH_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_HEADERS_PATCH_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_HEADERS_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq "                'username': self._http_username," "$GRANDSTREAM_PY"
  ! grep -Fq "                'Host': self._ip," "$GRANDSTREAM_PY"
  restored_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  echo "restored_sha256=$restored_sha"
  echo 'GRANDSTREAM-HEADERS-PATCH-ROLLBACK-PASS'
}

'''

if "inspect_grandstream_headers_patch()" not in text:
    anchor = "\ninstall_db_j129() {"
    if text.count(anchor) != 1:
        raise SystemExit("G10-15: install_db_j129 anchor not found exactly once")
    text = text.replace(anchor, "\n" + funcs + "install_db_j129() {", 1)

if "inspect-login-headers-patch)" not in text:
    anchor = '  rollback-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_login_patch ;;\n'
    repl = (
        anchor
        + '  inspect-login-headers-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_headers_patch ;;\n'
        + '  apply-login-headers-patch) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_headers_patch ;;\n'
        + '  rollback-login-headers-patch) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_headers_patch ;;\n'
    )
    if text.count(anchor) != 1:
        raise SystemExit("G10-15: case anchor not found exactly once")
    text = text.replace(anchor, repl, 1)

path.write_text(text, encoding="utf-8")
print("G10-15-HELPER-SOURCE-PREPARED")
