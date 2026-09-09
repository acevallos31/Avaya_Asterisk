#!/usr/bin/env python3
"""Inject reversible G10-16 Grandstream session propagation actions into the authorized LAB helper source.

The generated helper patch preserves G10-14 (username+password) and G10-15
(Host+Referer) and adds cookie propagation from /cgi-bin/dologin to
/cgi-bin/api.values.post. Cookie/SID values are never printed.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare-g10-16-helper.py <helper-path>")

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

if "GRANDSTREAM_SESSION_PATCH_BACKUP=" not in text:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    repl = anchor + 'GRANDSTREAM_SESSION_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-16"\n'
    if text.count(anchor) != 1:
        raise SystemExit("G10-16: backup variable anchor not found exactly once")
    text = text.replace(anchor, repl, 1)

funcs = r'''
inspect_grandstream_session_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  local username_count host_count referer_count cookie_collect_count cookie_header_count file_sha
  username_count="$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  cookie_collect_count="$(grep -Fxc "            cookie_parts = []" "$GRANDSTREAM_PY" || true)"
  cookie_header_count="$(grep -Fxc "                headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY" || true)"
  file_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  echo '=== GRANDSTREAM GXP16xx SESSION PROPAGATION PATCH AUDIT ==='
  echo "grandstream_py_sha256=$file_sha"
  echo "username_payload_line_count=$username_count"
  echo "host_header_line_count=$host_count"
  echo "referer_header_line_count=$referer_count"
  echo "cookie_collect_line_count=$cookie_collect_count"
  echo "cookie_header_line_count=$cookie_header_count"
  if [ -f "$GRANDSTREAM_SESSION_PATCH_BACKUP" ]; then
    echo 'g10_16_backup_present=YES'
    echo "g10_16_backup_sha256=$(sha256sum "$GRANDSTREAM_SESSION_PATCH_BACKUP" | awk '{print $1}')"
  else
    echo 'g10_16_backup_present=NO'
  fi
  if [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] && [ "$cookie_collect_count" -eq 0 ] && [ "$cookie_header_count" -eq 0 ]; then
    echo 'session_patch_state=READY'
  elif [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] && [ "$cookie_collect_count" -eq 1 ] && [ "$cookie_header_count" -eq 1 ]; then
    echo 'session_patch_state=PATCHED'
  else
    echo 'session_patch_state=UNEXPECTED'
    exit 1
  fi
  echo 'GRANDSTREAM-SESSION-PATCH-INSPECT-PASS'
}

apply_grandstream_session_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  install -d -o root -g root -m 0700 "$STATE_DIR"
  local username_count host_count referer_count cookie_collect_count cookie_header_count before_sha after_sha tmp
  username_count="$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  cookie_collect_count="$(grep -Fxc "            cookie_parts = []" "$GRANDSTREAM_PY" || true)"
  cookie_header_count="$(grep -Fxc "                headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY" || true)"
  if [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] && [ "$cookie_collect_count" -eq 1 ] && [ "$cookie_header_count" -eq 1 ]; then
    echo 'GRANDSTREAM-SESSION-PATCH-ALREADY-PRESENT'
    return 0
  fi
  [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] && [ "$cookie_collect_count" -eq 0 ] && [ "$cookie_header_count" -eq 0 ] || { echo 'ERROR: G10-14/G10-15 no están aplicados o el baseline es inesperado; apply cancelado.' >&2; exit 1; }
  [ ! -e "$GRANDSTREAM_SESSION_PATCH_BACKUP" ] || { echo "ERROR: ya existe backup G10-16 pendiente: $GRANDSTREAM_SESSION_PATCH_BACKUP" >&2; exit 1; }
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_SESSION_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_SESSION_PATCH_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.g10-16.XXXXXX")"
  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY2'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
old = """            body = response.read().decode('utf-8')\n\n            content_type = response.headers.get('Content-Type', '').split(';', 1)[0]"""
new = """            body = response.read().decode('utf-8')\n\n            # Preserve the authenticated web session for the subsequent API POST.\n            # Some GXP16xx firmware returns SID plus Set-Cookie headers and rejects\n            # api.values.post with session-expired when those cookies are omitted.\n            cookie_parts = []\n            for header_name, header_value in response.getheaders():\n                if header_name.lower() == 'set-cookie':\n                    cookie_pair = header_value.split(';', 1)[0].strip()\n                    if cookie_pair:\n                        cookie_parts.append(cookie_pair)\n            if cookie_parts:\n                headers['Cookie'] = '; '.join(cookie_parts)\n\n            content_type = response.headers.get('Content-Type', '').split(';', 1)[0]"""
if text.count(old) != 1:
    raise SystemExit('G10-16 expected exactly one dologin response block')
text = text.replace(old, new, 1)
open(dst, 'w', encoding='utf-8').write(text)
PY2
  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: el SHA no cambió después de G10-16.' >&2; exit 1; }
  grep -Fq "            cookie_parts = []" "$GRANDSTREAM_PY"
  grep -Fq "                headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY"
  echo "before_sha256=$before_sha"
  echo "after_sha256=$after_sha"
  echo 'GRANDSTREAM-SESSION-PATCH-APPLY-PASS'
}

rollback_grandstream_session_patch() {
  [ -f "$GRANDSTREAM_SESSION_PATCH_BACKUP" ] || { echo 'ERROR: no existe backup controlado G10-16.' >&2; exit 1; }
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  local cookie_collect_count cookie_header_count restored_sha
  cookie_collect_count="$(grep -Fxc "            cookie_parts = []" "$GRANDSTREAM_PY" || true)"
  cookie_header_count="$(grep -Fxc "                headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY" || true)"
  [ "$cookie_collect_count" -eq 1 ] && [ "$cookie_header_count" -eq 1 ] || { echo 'ERROR: el live file no contiene G10-16; rollback cancelado.' >&2; exit 1; }
  python3 -m py_compile "$GRANDSTREAM_SESSION_PATCH_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_SESSION_PATCH_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_SESSION_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq "                'Host': self._ip," "$GRANDSTREAM_PY"
  grep -Fq "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY"
  ! grep -Fq "            cookie_parts = []" "$GRANDSTREAM_PY"
  restored_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  echo "restored_sha256=$restored_sha"
  echo 'GRANDSTREAM-SESSION-PATCH-ROLLBACK-PASS'
}

'''

if "inspect_grandstream_session_patch()" not in text:
    anchor = "\ninstall_db_j129() {"
    if text.count(anchor) != 1:
        raise SystemExit("G10-16: install_db_j129 anchor not found exactly once")
    text = text.replace(anchor, "\n" + funcs + "install_db_j129() {", 1)

if "inspect-session-patch)" not in text:
    anchor = '  rollback-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_login_patch ;;\n'
    repl = anchor + '  inspect-session-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_session_patch ;;\n  apply-session-patch) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_session_patch ;;\n  rollback-session-patch) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_session_patch ;;\n'
    if text.count(anchor) != 1:
        raise SystemExit("G10-16: case anchor not found exactly once")
    text = text.replace(anchor, repl, 1)

path.write_text(text, encoding="utf-8")
