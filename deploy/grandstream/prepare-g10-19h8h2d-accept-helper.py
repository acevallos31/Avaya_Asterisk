#!/usr/bin/env python3
"""Prepare a reversible H8H2D Accept header patch for GXP140x native login.

G10-18B proved the curl Host+Referer login path returns a SID while H8H2C proved
the native http.client path parses login JSON but stops before SID_READY. One
observable request difference is curl's `Accept: */*`. This patch tests only
that delta and logs no credentials or session values.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8H2D_PATCH_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2D backup anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8H2D_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8h2d"\n', 1)

funcs = r'''

apply_grandstream_h8h2d_accept_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  if grep -Fq '# G10-19H8H2D-ACCEPT-HEADER' "$GRANDSTREAM_PY"; then
    echo 'GRANDSTREAM-H8H2D-ACCEPT-PATCH-ALREADY-PRESENT'; return 0
  fi
  [ ! -e "$GRANDSTREAM_H8H2D_PATCH_BACKUP" ] || {
    echo 'ERROR: H8H2D backup already exists; refusing overwrite.' >&2; exit 1;
  }
  local tmp
  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2D_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8H2D_PATCH_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8h2d.XXXXXX")"

  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
marker = '    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start = text.find(marker)
if start < 0:
    raise SystemExit('H8H2D GXP140x function missing')
next_def = text.find('\n    def ', start + len(marker))
end = len(text) if next_def < 0 else next_def
prefix, body, suffix = text[:start], text[start:end], text[end:]
old = """            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': self._ip,
                'Referer': 'http://%s/' % self._ip,
            }
"""
new = """            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                # G10-19H8H2D-ACCEPT-HEADER
                'Accept': '*/*',
                'Host': self._ip,
                'Referer': 'http://%s/' % self._ip,
            }
"""
if body.count(old) != 1:
    raise SystemExit('H8H2D expected exactly one native headers block')
body = body.replace(old, new, 1)
open(dst, 'w', encoding='utf-8').write(prefix + body + suffix)
PY

  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq '# G10-19H8H2D-ACCEPT-HEADER' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2D-ACCEPT-PATCH-APPLY-PASS'
}

rollback_grandstream_h8h2d_accept_patch() {
  [ -f "$GRANDSTREAM_H8H2D_PATCH_BACKUP" ] || { echo 'ERROR: H8H2D backup absent.' >&2; exit 1; }
  grep -Fq '# G10-19H8H2D-ACCEPT-HEADER' "$GRANDSTREAM_PY" || {
    echo 'ERROR: H8H2D marker absent; rollback cancelled.' >&2; exit 1;
  }
  python3 -m py_compile "$GRANDSTREAM_H8H2D_PATCH_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_H8H2D_PATCH_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8H2D_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  ! grep -Fq '# G10-19H8H2D-ACCEPT-HEADER' "$GRANDSTREAM_PY"
  echo 'GRANDSTREAM-H8H2D-ACCEPT-PATCH-ROLLBACK-PASS'
}
'''

if 'apply_grandstream_h8h2d_accept_patch()' not in s:
    anchor = '\n[ -n "$ACTION" ] || usage\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2D helper action anchor missing')
    s = s.replace(anchor, funcs + anchor, 1)

if 'apply-grandstream-h8h2d-accept-patch)' not in s:
    case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;\n'
    if s.count(case_anchor) != 1:
        raise SystemExit('H8H2D helper case anchor missing')
    s = s.replace(case_anchor, case_anchor
        + '  apply-grandstream-h8h2d-accept-patch) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8h2d_accept_patch ;;\n'
        + '  rollback-grandstream-h8h2d-accept-patch) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8h2d_accept_patch ;;\n', 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8H2D-ACCEPT-HELPER-PREPARE=PASS')
