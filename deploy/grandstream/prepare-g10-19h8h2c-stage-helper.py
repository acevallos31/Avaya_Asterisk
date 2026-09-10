#!/usr/bin/env python3
"""Prepare reversible H8H2C stage tracing for the native GXP140x flow.

Only fixed stage names are logged. No SID, cookie, password, SIP secret, response
body, or submitted P-value is emitted.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8H2C_PATCH_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2C: backup anchor not found exactly once')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8H2C_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8h2c"\n', 1)

funcs = r'''

apply_grandstream_h8h2c_stage_trace() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY" || {
    echo 'ERROR: H8H2 must be present before H8H2C.' >&2; exit 1;
  }
  if grep -Fq '# G10-19H8H2C-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"; then
    echo 'GRANDSTREAM-H8H2C-STAGE-TRACE-ALREADY-PRESENT'; return 0
  fi
  [ ! -e "$GRANDSTREAM_H8H2C_PATCH_BACKUP" ] || {
    if cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2C_PATCH_BACKUP"; then
      rm -f "$GRANDSTREAM_H8H2C_PATCH_BACKUP"
      echo 'stale_h8h2c_backup_cleanup=SAFE_MATCH_REMOVED'
    else
      echo 'ERROR: H8H2C differing backup exists; refusing overwrite.' >&2; exit 1
    fi
  }

  local tmp
  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2C_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8H2C_PATCH_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8h2c.XXXXXX")"

  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
marker = '    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start = text.find(marker)
if start < 0:
    raise SystemExit('H8H2C GXP140x function not found')
next_def = text.find('\n    def ', start + len(marker))
end = len(text) if next_def < 0 else next_def
prefix, body, suffix = text[:start], text[start:end], text[end:]

repls = [
    ("        try:\n            # Login into interface and get SID. Check proper Content-Type\n",
     "        try:\n            # G10-19H8H2C-SAFE-STAGE-TRACE\n            logging.error('G10-19H8H2C-STAGE=ENTER')\n            # Login into interface and get SID. Check proper Content-Type\n"),
    ("            response = conn.getresponse()\n\n            body = response.read().decode('utf-8')\n",
     "            response = conn.getresponse()\n            logging.error('G10-19H8H2C-STAGE=LOGIN_RESPONSE')\n\n            body = response.read().decode('utf-8')\n"),
    ("            jsonvars = json.loads(body)\n",
     "            jsonvars = json.loads(body)\n            logging.error('G10-19H8H2C-STAGE=LOGIN_JSON_PARSED')\n"),
    ("            sid = jsonvars['body']['sid']\n",
     "            sid = jsonvars['body']['sid']\n            logging.error('G10-19H8H2C-STAGE=SID_READY')\n"),
    ("            conn.request('POST', '/cgi-bin/api.values.post', body=payload, headers=headers)\n",
     "            logging.error('G10-19H8H2C-STAGE=POST_BEGIN')\n            conn.request('POST', '/cgi-bin/api.values.post', body=payload, headers=headers)\n"),
    ("            response = conn.getresponse()\n\n            jsonvars = self._parseBotchedJSONResponse(response)\n",
     "            response = conn.getresponse()\n            logging.error('G10-19H8H2C-STAGE=POST_RESPONSE')\n\n            jsonvars = self._parseBotchedJSONResponse(response)\n            logging.error('G10-19H8H2C-STAGE=POST_JSON_PARSED')\n"),
]
for old, new in repls:
    if body.count(old) != 1:
        raise SystemExit('H8H2C anchor count mismatch for safe stage instrumentation')
    body = body.replace(old, new, 1)
open(dst, 'w', encoding='utf-8').write(prefix + body + suffix)
PY

  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq '# G10-19H8H2C-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2C-STAGE-TRACE-APPLY-PASS'
}

rollback_grandstream_h8h2c_stage_trace() {
  if grep -Fq '# G10-19H8H2C-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"; then
    [ -f "$GRANDSTREAM_H8H2C_PATCH_BACKUP" ] || { echo 'ERROR: H8H2C marker present but backup absent.' >&2; exit 1; }
    python3 -m py_compile "$GRANDSTREAM_H8H2C_PATCH_BACKUP"
    install -o root -g root -m 0644 "$GRANDSTREAM_H8H2C_PATCH_BACKUP" "$GRANDSTREAM_PY"
    rm -f "$GRANDSTREAM_H8H2C_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
    grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY"
    ! grep -Fq '# G10-19H8H2C-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"
    echo 'GRANDSTREAM-H8H2C-STAGE-TRACE-ROLLBACK-PASS'
    return 0
  fi
  if [ -f "$GRANDSTREAM_H8H2C_PATCH_BACKUP" ] && cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2C_PATCH_BACKUP"; then
    rm -f "$GRANDSTREAM_H8H2C_PATCH_BACKUP"
    echo 'stale_h8h2c_backup_cleanup=SAFE_MATCH_REMOVED'
  fi
  echo 'GRANDSTREAM-H8H2C-STAGE-TRACE-ROLLBACK=ALREADY_CLEAN'
}
'''

if 'apply_grandstream_h8h2c_stage_trace()' not in s:
    anchor = '\n[ -n "$ACTION" ] || usage\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2C helper action anchor missing')
    s = s.replace(anchor, funcs + anchor, 1)

if 'apply-grandstream-h8h2c-stage-trace)' not in s:
    case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;\n'
    if s.count(case_anchor) != 1:
        raise SystemExit('H8H2C helper case anchor missing')
    s = s.replace(case_anchor, case_anchor
        + '  apply-grandstream-h8h2c-stage-trace) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8h2c_stage_trace ;;\n'
        + '  rollback-grandstream-h8h2c-stage-trace) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8h2c_stage_trace ;;\n', 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8H2C-STAGE-HELPER-PREPARE=PASS')
