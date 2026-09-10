#!/usr/bin/env python3
"""Prepare reversible G10-19H8I request-fidelity patch for GXP140x login.

H8H2H proved that the stock Python client succeeds with the known-good password
when login includes Accept */* and a curl-like User-Agent in addition to the
existing Host/Referer/Content-Type headers. This patch changes only those headers
inside _enableStaticProvisioning_GXP140x and logs no secret/session values.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8I_FIDELITY_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8I fidelity backup anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8I_FIDELITY_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8i-fidelity"\n', 1)

funcs = r'''

apply_grandstream_h8i_request_fidelity() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  if grep -Fq '# G10-19H8I-REQUEST-FIDELITY' "$GRANDSTREAM_PY"; then
    echo 'GRANDSTREAM-H8I-REQUEST-FIDELITY=ALREADY_PRESENT'; return 0
  fi
  [ ! -e "$GRANDSTREAM_H8I_FIDELITY_BACKUP" ] || {
    if cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8I_FIDELITY_BACKUP"; then
      rm -f "$GRANDSTREAM_H8I_FIDELITY_BACKUP"
      echo 'stale_h8i_fidelity_backup_cleanup=SAFE_MATCH_REMOVED'
    else
      echo 'ERROR: differing H8I fidelity backup exists; refusing overwrite' >&2; exit 1
    fi
  }
  local tmp
  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8I_FIDELITY_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8I_FIDELITY_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8i-fidelity.XXXXXX")"
  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
marker = '    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start = text.find(marker)
if start < 0:
    raise SystemExit('H8I GXP140x function missing')
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
                # G10-19H8I-REQUEST-FIDELITY
                'Accept': '*/*',
                'User-Agent': 'curl/8.14.1',
                'Host': self._ip,
                'Referer': 'http://%s/' % self._ip,
            }
"""
if body.count(old) != 1:
    raise SystemExit('H8I expected exactly one GXP140x headers block')
body = body.replace(old, new, 1)
open(dst, 'w', encoding='utf-8').write(prefix + body + suffix)
PY
  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq '# G10-19H8I-REQUEST-FIDELITY' "$GRANDSTREAM_PY"
  grep -Fq "'Accept': '*/*'" "$GRANDSTREAM_PY"
  grep -Fq "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8I-REQUEST-FIDELITY-APPLY-PASS'
}

rollback_grandstream_h8i_request_fidelity() {
  if grep -Fq '# G10-19H8I-REQUEST-FIDELITY' "$GRANDSTREAM_PY"; then
    [ -f "$GRANDSTREAM_H8I_FIDELITY_BACKUP" ] || { echo 'ERROR: H8I fidelity marker present but backup absent' >&2; exit 1; }
    python3 -m py_compile "$GRANDSTREAM_H8I_FIDELITY_BACKUP"
    install -o root -g root -m 0644 "$GRANDSTREAM_H8I_FIDELITY_BACKUP" "$GRANDSTREAM_PY"
    rm -f "$GRANDSTREAM_H8I_FIDELITY_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
    ! grep -Fq '# G10-19H8I-REQUEST-FIDELITY' "$GRANDSTREAM_PY"
    echo 'GRANDSTREAM-H8I-REQUEST-FIDELITY-ROLLBACK-PASS'
    return 0
  fi
  if [ -f "$GRANDSTREAM_H8I_FIDELITY_BACKUP" ] && cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8I_FIDELITY_BACKUP"; then
    rm -f "$GRANDSTREAM_H8I_FIDELITY_BACKUP"
    echo 'stale_h8i_fidelity_backup_cleanup=SAFE_MATCH_REMOVED'
  fi
  echo 'GRANDSTREAM-H8I-REQUEST-FIDELITY-ROLLBACK=ALREADY_CLEAN'
}
'''

anchor = '\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor) != 1:
    raise SystemExit('H8I fidelity helper action anchor missing')
if 'apply_grandstream_h8i_request_fidelity()' not in s:
    s = s.replace(anchor, funcs + anchor, 1)

case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8I fidelity helper case anchor missing')
if 'apply-grandstream-h8i-request-fidelity)' not in s:
    s = s.replace(case_anchor, case_anchor
        + '\n  apply-grandstream-h8i-request-fidelity) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8i_request_fidelity ;;'
        + '\n  rollback-grandstream-h8i-request-fidelity) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8i_request_fidelity ;;', 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8I-FIDELITY-HELPER-PREPARE=PASS')
