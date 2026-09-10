#!/usr/bin/env python3
"""Prepare reversible H8H2E safe classification of native login JSON shape."""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
if 'GRANDSTREAM_H8H2E_PATCH_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2E backup anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8H2E_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8h2e"\n', 1)

funcs = r'''

apply_grandstream_h8h2e_login_shape() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  if grep -Fq '# G10-19H8H2E-SAFE-LOGIN-SHAPE' "$GRANDSTREAM_PY"; then
    echo 'GRANDSTREAM-H8H2E-LOGIN-SHAPE-ALREADY-PRESENT'; return 0
  fi
  [ ! -e "$GRANDSTREAM_H8H2E_PATCH_BACKUP" ] || { echo 'ERROR: H8H2E backup exists' >&2; exit 1; }
  local tmp
  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2E_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8H2E_PATCH_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8h2e.XXXXXX")"
  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src,dst=sys.argv[1],sys.argv[2]
text=open(src,'r',encoding='utf-8').read()
marker='    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start=text.find(marker)
if start<0: raise SystemExit('H8H2E GXP140x function missing')
next_def=text.find('\n    def ',start+len(marker)); end=len(text) if next_def<0 else next_def
prefix,body,suffix=text[:start],text[start:end],text[end:]
anchor="            jsonvars = json.loads(body)\n"
if body.count(anchor)!=1: raise SystemExit('H8H2E login JSON anchor mismatch')
block=anchor+"""            # G10-19H8H2E-SAFE-LOGIN-SHAPE
            response_success = isinstance(jsonvars, dict) and jsonvars.get('response') == 'success'
            body_dict = isinstance(jsonvars, dict) and isinstance(jsonvars.get('body'), dict)
            sid_present = body_dict and bool(jsonvars['body'].get('sid'))
            logging.error('G10-19H8H2E-LOGIN-CLASS response_success=%s body_dict=%s sid_present=%s' %
                          ('YES' if response_success else 'NO', 'YES' if body_dict else 'NO', 'YES' if sid_present else 'NO'))
"""
body=body.replace(anchor,block,1)
open(dst,'w',encoding='utf-8').write(prefix+body+suffix)
PY
  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq '# G10-19H8H2E-SAFE-LOGIN-SHAPE' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2E-LOGIN-SHAPE-APPLY-PASS'
}

rollback_grandstream_h8h2e_login_shape() {
  [ -f "$GRANDSTREAM_H8H2E_PATCH_BACKUP" ] || { echo 'ERROR: H8H2E backup absent' >&2; exit 1; }
  grep -Fq '# G10-19H8H2E-SAFE-LOGIN-SHAPE' "$GRANDSTREAM_PY" || { echo 'ERROR: H8H2E marker absent' >&2; exit 1; }
  python3 -m py_compile "$GRANDSTREAM_H8H2E_PATCH_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_H8H2E_PATCH_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8H2E_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  ! grep -Fq '# G10-19H8H2E-SAFE-LOGIN-SHAPE' "$GRANDSTREAM_PY"
  echo 'GRANDSTREAM-H8H2E-LOGIN-SHAPE-ROLLBACK-PASS'
}
'''
if 'apply_grandstream_h8h2e_login_shape()' not in s:
    anchor='\n[ -n "$ACTION" ] || usage\n'
    if s.count(anchor)!=1: raise SystemExit('H8H2E action anchor missing')
    s=s.replace(anchor,funcs+anchor,1)
if 'apply-grandstream-h8h2e-login-shape)' not in s:
    anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;\n'
    if s.count(anchor)!=1: raise SystemExit('H8H2E case anchor missing')
    s=s.replace(anchor,anchor
      +'  apply-grandstream-h8h2e-login-shape) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8h2e_login_shape ;;\n'
      +'  rollback-grandstream-h8h2e-login-shape) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8h2e_login_shape ;;\n',1)
p.write_text(s,encoding='utf-8')
print('G10-19H8H2E-LOGIN-SHAPE-HELPER-PREPARE=PASS')
