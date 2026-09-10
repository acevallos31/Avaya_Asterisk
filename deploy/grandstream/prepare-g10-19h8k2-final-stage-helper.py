#!/usr/bin/env python3
"""Prepare reversible H8K2 tracing for the persisted H8J native flow.

Only fixed stage names plus sanitized response/status class tokens are emitted.
No SID, cookie, password, SIP secret, response body or P-value payload is logged.
Run after prepare-integrated-applyconfig-helper.py so its sanitized output can be
extended to surface the fixed H8K2 markers.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8K2_TRACE_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8K2 backup anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8K2_TRACE_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8k2-trace"\n', 1)

funcs = r'''

apply_grandstream_h8k2_final_stage_trace() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  grep -Fq '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY" || { echo 'ERROR: H8J final native patch must already be active' >&2; exit 1; }
  if grep -Fq '# G10-19H8K2-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"; then
    echo 'G10-19H8K2-STAGE-TRACE=ALREADY_PRESENT'; return 0
  fi
  [ ! -e "$GRANDSTREAM_H8K2_TRACE_BACKUP" ] || {
    if cmp -s "$GRANDSTREAM_PY" "$GRANDSTREAM_H8K2_TRACE_BACKUP"; then
      rm -f "$GRANDSTREAM_H8K2_TRACE_BACKUP"
      echo 'stale_h8k2_trace_backup_cleanup=SAFE_MATCH_REMOVED'
    else
      echo 'ERROR: differing H8K2 trace backup exists' >&2; exit 1
    fi
  }

  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8K2_TRACE_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8K2_TRACE_BACKUP"
  local tmp
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8k2.XXXXXX")"

  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
marker = '    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start = text.find(marker)
if start < 0:
    raise SystemExit('H8K2 GXP140x function missing')
next_def = text.find('\n    def ', start + len(marker))
end = len(text) if next_def < 0 else next_def
prefix, body, suffix = text[:start], text[start:end], text[end:]

repls = [
    ("        try:\n            # Login into interface and get SID. Check proper Content-Type\n",
     "        try:\n            # G10-19H8K2-SAFE-STAGE-TRACE\n            logging.error('G10-19H8K2-STAGE=ENTER')\n            # Login into interface and get SID. Check proper Content-Type\n"),
    ("            response = conn.getresponse()\n\n            body = response.read().decode('utf-8')\n",
     "            response = conn.getresponse()\n            logging.error('G10-19H8K2-STAGE=LOGIN_RESPONSE')\n\n            body = response.read().decode('utf-8')\n"),
    ("            jsonvars = json.loads(body)\n",
     "            jsonvars = json.loads(body)\n            logging.error('G10-19H8K2-STAGE=LOGIN_JSON_PARSED')\n"),
    ("            sid = jsonvars['body']['sid']\n",
     "            sid = jsonvars['body']['sid']\n            logging.error('G10-19H8K2-STAGE=SID_READY')\n"),
    ("            conn.request('POST', '/cgi-bin/api.values.post', body=payload, headers=headers)\n",
     "            logging.error('G10-19H8K2-STAGE=POST_BEGIN')\n            conn.request('POST', '/cgi-bin/api.values.post', body=payload, headers=headers)\n"),
    ("            response = conn.getresponse()\n\n            jsonvars = self._parseBotchedJSONResponse(response)\n",
     "            response = conn.getresponse()\n            logging.error('G10-19H8K2-STAGE=POST_RESPONSE')\n\n            jsonvars = self._parseBotchedJSONResponse(response)\n            logging.error('G10-19H8K2-STAGE=POST_JSON_PARSED')\n            response_class = 'NON_DICT'\n            status_class = 'NONE'\n            if isinstance(jsonvars, dict):\n                response_class = str(jsonvars.get('response', 'NONE'))\n                if isinstance(jsonvars.get('body'), dict):\n                    status_class = str(jsonvars['body'].get('status', 'NONE'))\n            response_class = ''.join(c if (c.isalnum() or c in '_.-') else '_' for c in response_class)[:40] or 'EMPTY'\n            status_class = ''.join(c if (c.isalnum() or c in '_.-') else '_' for c in status_class)[:40] or 'EMPTY'\n            logging.error('G10-19H8K2-POST-CLASS response=%s status=%s' % (response_class, status_class))\n"),
]
for old, new in repls:
    if body.count(old) != 1:
        raise SystemExit('H8K2 anchor count mismatch')
    body = body.replace(old, new, 1)
open(dst, 'w', encoding='utf-8').write(prefix + body + suffix)
PY

  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq '# G10-19H8K2-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'G10-19H8K2-STAGE-TRACE-APPLY-PASS'
}

rollback_grandstream_h8k2_final_stage_trace() {
  if grep -Fq '# G10-19H8K2-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"; then
    [ -f "$GRANDSTREAM_H8K2_TRACE_BACKUP" ] || { echo 'ERROR: H8K2 marker present but backup absent' >&2; exit 1; }
    python3 -m py_compile "$GRANDSTREAM_H8K2_TRACE_BACKUP"
    install -o root -g root -m 0644 "$GRANDSTREAM_H8K2_TRACE_BACKUP" "$GRANDSTREAM_PY"
    rm -f "$GRANDSTREAM_H8K2_TRACE_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
    grep -Fq '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY"
    ! grep -Fq '# G10-19H8K2-SAFE-STAGE-TRACE' "$GRANDSTREAM_PY"
    echo 'G10-19H8K2-STAGE-TRACE-ROLLBACK-PASS'
    return 0
  fi
  echo 'G10-19H8K2-STAGE-TRACE-ROLLBACK=ALREADY_CLEAN'
}
'''

anchor = '\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor) != 1:
    raise SystemExit('H8K2 action anchor missing')
if 'apply_grandstream_h8k2_final_stage_trace()' not in s:
    s = s.replace(anchor, funcs + anchor, 1)

case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8K2 case anchor missing')
if 'apply-grandstream-h8k2-final-stage-trace)' not in s:
    s = s.replace(case_anchor, case_anchor
        + '\n  apply-grandstream-h8k2-final-stage-trace) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8k2_final_stage_trace ;;'
        + '\n  rollback-grandstream-h8k2-final-stage-trace) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8k2_final_stage_trace ;;', 1)

# Extend only the sanitized integrated helper output with fixed H8K2 markers.
out_anchor = "  echo 'applyconfig_end_seen='$(grep -Fq 'END ENDPOINT CONFIGURATION' \"$raw\" && echo YES || echo NO)\n"
if s.count(out_anchor) != 1:
    raise SystemExit('H8K2 integrated output anchor missing; run prepare-integrated-applyconfig-helper.py first')
if '# G10-19H8K2-SAFE-OUTPUT' not in s:
    out_block = out_anchor + r'''

  # G10-19H8K2-SAFE-OUTPUT
  local h8k2_stages h8k2_class
  h8k2_stages="$(grep -Eo 'G10-19H8K2-STAGE=[A-Z_]+' "$raw" || true)"
  h8k2_class="$(grep -Eo 'G10-19H8K2-POST-CLASS response=[A-Za-z0-9_.-]{1,40} status=[A-Za-z0-9_.-]{1,40}' "$raw" | tail -n 1 || true)"
  if [ -n "$h8k2_stages" ]; then
    echo 'h8k2_stage_trace_seen=YES'
    printf '%s\n' "$h8k2_stages"
  else
    echo 'h8k2_stage_trace_seen=NO'
  fi
  if [ -n "$h8k2_class" ]; then
    echo 'h8k2_post_class_seen=YES'
    printf '%s\n' "$h8k2_class"
  else
    echo 'h8k2_post_class_seen=NO'
  fi
'''
    s = s.replace(out_anchor, out_block, 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8K2-HELPER-PREPARE=PASS')
