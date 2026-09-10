#!/usr/bin/env python3
"""Prepare a temporary, reversible H8H2B response-class diagnostic patch.

The live patch emits only two whitelisted response fields (response/status),
sanitarized to a short token. It never logs SID, cookies, passwords, SIP secrets,
or the submitted P-value payload.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8H2B_PATCH_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2B: backup anchor not found exactly once')
    s = s.replace(
        anchor,
        anchor + 'GRANDSTREAM_H8H2B_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8h2b"\n',
        1,
    )

funcs = r'''

apply_grandstream_h8h2b_response_classifier() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY" || {
    echo 'ERROR: H8H2 session patch must be present before H8H2B diagnostic.' >&2
    exit 1
  }
  if grep -Fq '# G10-19H8H2B-SAFE-RESPONSE-CLASS' "$GRANDSTREAM_PY"; then
    echo 'GRANDSTREAM-H8H2B-RESPONSE-CLASSIFIER-ALREADY-PRESENT'
    return 0
  fi
  [ ! -e "$GRANDSTREAM_H8H2B_PATCH_BACKUP" ] || {
    echo 'ERROR: H8H2B backup already exists; refusing overwrite.' >&2
    exit 1
  }

  local tmp before_sha after_sha
  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2B_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8H2B_PATCH_BACKUP"
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8h2b.XXXXXX")"

  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
anchor = "            jsonvars = self._parseBotchedJSONResponse(response)\n"
if text.count(anchor) != 1:
    raise SystemExit('H8H2B expected exactly one GXP140x response parse anchor')
block = """            jsonvars = self._parseBotchedJSONResponse(response)
            # G10-19H8H2B-SAFE-RESPONSE-CLASS
            response_class = 'NON_DICT'
            status_class = 'NONE'
            if isinstance(jsonvars, dict):
                response_class = str(jsonvars.get('response', 'NONE'))
                if isinstance(jsonvars.get('body'), dict):
                    status_class = str(jsonvars['body'].get('status', 'NONE'))
            response_class = re.sub(r'[^A-Za-z0-9_.-]', '_', response_class)[:40] or 'EMPTY'
            status_class = re.sub(r'[^A-Za-z0-9_.-]', '_', status_class)[:40] or 'EMPTY'
            logging.error('G10-19H8H2B-RESPONSE-CLASS response=%s status=%s' %
                          (response_class, status_class))
"""
text = text.replace(anchor, block, 1)
open(dst, 'w', encoding='utf-8').write(text)
PY

  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: H8H2B SHA unchanged.' >&2; exit 1; }
  grep -Fq '# G10-19H8H2B-SAFE-RESPONSE-CLASS' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2B-RESPONSE-CLASSIFIER-APPLY-PASS'
}

rollback_grandstream_h8h2b_response_classifier() {
  [ -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP" ] || { echo 'ERROR: no H8H2B backup exists.' >&2; exit 1; }
  grep -Fq '# G10-19H8H2B-SAFE-RESPONSE-CLASS' "$GRANDSTREAM_PY" || {
    echo 'ERROR: H8H2B marker absent; rollback cancelled.' >&2
    exit 1
  }
  python3 -m py_compile "$GRANDSTREAM_H8H2B_PATCH_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_H8H2B_PATCH_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY"
  ! grep -Fq '# G10-19H8H2B-SAFE-RESPONSE-CLASS' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2B-RESPONSE-CLASSIFIER-ROLLBACK-PASS'
}
'''

if 'apply_grandstream_h8h2b_response_classifier()' not in s:
    anchor = '\n[ -n "$ACTION" ] || usage\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2B: helper action anchor not found exactly once')
    s = s.replace(anchor, funcs + anchor, 1)

if 'apply-grandstream-h8h2b-response-classifier)' not in s:
    case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;\n'
    if s.count(case_anchor) != 1:
        raise SystemExit('H8H2B: helper case anchor not found exactly once')
    s = s.replace(
        case_anchor,
        case_anchor
        + '  apply-grandstream-h8h2b-response-classifier) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8h2b_response_classifier ;;\n'
        + '  rollback-grandstream-h8h2b-response-classifier) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8h2b_response_classifier ;;\n',
        1,
    )

p.write_text(s, encoding='utf-8')
print('G10-19H8H2B-DIAGNOSTIC-HELPER-PREPARE=PASS')
