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

  # A previous failed diagnostic can leave a backup even though no H8H2B marker
  # was installed. Remove it only when it is byte-for-byte the same as the
  # current H8H2-patched live file; otherwise refuse to overwrite evidence.
  if [ -e "$GRANDSTREAM_H8H2B_PATCH_BACKUP" ]; then
    if cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2B_PATCH_BACKUP"; then
      rm -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP"
      echo 'stale_h8h2b_backup_cleanup=SAFE_MATCH_REMOVED'
    else
      echo 'ERROR: H8H2B backup exists and differs from live file; refusing overwrite.' >&2
      exit 1
    fi
  fi

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
fn_marker = '    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start = text.find(fn_marker)
if start < 0:
    raise SystemExit('H8H2B GXP140x function not found')
next_def = text.find('\n    def ', start + len(fn_marker))
end = len(text) if next_def < 0 else next_def
prefix, body, suffix = text[:start], text[start:end], text[end:]
anchor = "            jsonvars = self._parseBotchedJSONResponse(response)\n"
if body.count(anchor) != 1:
    raise SystemExit('H8H2B expected exactly one response parse anchor inside GXP140x')
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
body = body.replace(anchor, block, 1)
open(dst, 'w', encoding='utf-8').write(prefix + body + suffix)
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
  if grep -Fq '# G10-19H8H2B-SAFE-RESPONSE-CLASS' "$GRANDSTREAM_PY"; then
    [ -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP" ] || { echo 'ERROR: H8H2B marker present but backup absent.' >&2; exit 1; }
    python3 -m py_compile "$GRANDSTREAM_H8H2B_PATCH_BACKUP"
    install -o root -g root -m 0644 "$GRANDSTREAM_H8H2B_PATCH_BACKUP" "$GRANDSTREAM_PY"
    rm -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
    grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY"
    ! grep -Fq '# G10-19H8H2B-SAFE-RESPONSE-CLASS' "$GRANDSTREAM_PY"
    echo 'secret_values_logged=NO'
    echo 'GRANDSTREAM-H8H2B-RESPONSE-CLASSIFIER-ROLLBACK-PASS'
    return 0
  fi

  # If apply aborted before installing the marker, remove only an identical
  # stale backup. This leaves any differing backup untouched for manual review.
  if [ -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP" ]; then
    if cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2B_PATCH_BACKUP"; then
      rm -f "$GRANDSTREAM_H8H2B_PATCH_BACKUP"
      echo 'stale_h8h2b_backup_cleanup=SAFE_MATCH_REMOVED'
      echo 'GRANDSTREAM-H8H2B-RESPONSE-CLASSIFIER-ROLLBACK=ALREADY_CLEAN'
      return 0
    fi
    echo 'ERROR: H8H2B marker absent but backup differs; preserving backup for review.' >&2
    exit 1
  fi

  echo 'GRANDSTREAM-H8H2B-RESPONSE-CLASSIFIER-ROLLBACK=ALREADY_CLEAN'
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
