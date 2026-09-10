#!/usr/bin/env python3
"""Prepare reversible final native HTTP-session integration for GXP16xx.

Validated on GXP1625 firmware 1.0.7.70 by H8I. The live patch preserves the
existing G10-14/G10-15 login payload/Host/Referer behavior and adds:
- Accept: */*
- validated curl-like User-Agent
- propagation of Set-Cookie values from dologin
- client-side session-identity=<SID>, matching the real web UI contract

No credential, SID, cookie value, SIP secret or P-value payload is logged.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8J_FINAL_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8J backup anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8J_FINAL_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8j-final"\n', 1)

funcs = r'''

inspect_grandstream_h8j_final_native() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  local marker_count accept_count ua_count sid_count cookie_count
  marker_count="$(grep -Fc '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY" || true)"
  accept_count="$(grep -Fc "'Accept': '*/*'" "$GRANDSTREAM_PY" || true)"
  ua_count="$(grep -Fc "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY" || true)"
  sid_count="$(grep -Fc "cookie_parts.append('session-identity=' + sid)" "$GRANDSTREAM_PY" || true)"
  cookie_count="$(grep -Fc "headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY" || true)"
  echo 'scope=G10_19H8J_FINAL_NATIVE_AUDIT'
  echo 'secret_values_logged=NO'
  echo "final_marker_count=$marker_count"
  echo "accept_header_count=$accept_count"
  echo "validated_user_agent_count=$ua_count"
  echo "session_identity_synth_count=$sid_count"
  echo "cookie_header_count=$cookie_count"
  if [ "$marker_count" -eq 0 ] && [ "$sid_count" -eq 0 ]; then
    echo 'h8j_state=READY'
  elif [ "$marker_count" -ge 2 ] && [ "$accept_count" -ge 1 ] && [ "$ua_count" -ge 1 ] && [ "$sid_count" -eq 1 ] && [ "$cookie_count" -ge 1 ]; then
    echo 'h8j_state=PATCHED'
  else
    echo 'h8j_state=UNEXPECTED'
    return 1
  fi
  echo 'G10-19H8J-FINAL-NATIVE-INSPECT-PASS'
}

apply_grandstream_h8j_final_native() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  if grep -Fq '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY"; then
    inspect_grandstream_h8j_final_native
    return 0
  fi
  [ "$(grep -Fc '# G10-19H6-INTEGRATED-XML-GENERATOR' "$GRANDSTREAM_PY" || true)" -ge 1 ] || { echo 'ERROR: H6 XML generator missing' >&2; exit 1; }
  [ "$(grep -Fc '# G10-19H8F0-SAFE-ERROR-LOGGING' "$GRANDSTREAM_PY" || true)" -ge 2 ] || { echo 'ERROR: safe error logging missing' >&2; exit 1; }
  [ "$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)" -eq 1 ] || { echo 'ERROR: username login payload baseline missing' >&2; exit 1; }
  [ "$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)" -eq 1 ] || { echo 'ERROR: Host header baseline missing' >&2; exit 1; }
  [ "$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)" -eq 1 ] || { echo 'ERROR: Referer header baseline missing' >&2; exit 1; }
  [ ! -e "$GRANDSTREAM_H8J_FINAL_BACKUP" ] || { echo 'ERROR: H8J backup already exists' >&2; exit 1; }

  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8J_FINAL_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8J_FINAL_BACKUP"
  local tmp before_sha after_sha
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8j.XXXXXX")"

  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
marker = '    def _enableStaticProvisioning_GXP140x(self, vars):\n'
start = text.find(marker)
if start < 0:
    raise SystemExit('H8J GXP140x function missing')
next_def = text.find('\n    def ', start + len(marker))
end = len(text) if next_def < 0 else next_def
prefix, body, suffix = text[:start], text[start:end], text[end:]

old_headers = """            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': self._ip,
                'Referer': 'http://%s/' % self._ip,
            }
"""
new_headers = """            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                # G10-19H8J-FINAL-NATIVE-GXP16XX — request fidelity validated on GXP1625 1.0.7.70
                'Accept': '*/*',
                'User-Agent': 'curl/8.14.1',
                'Host': self._ip,
                'Referer': 'http://%s/' % self._ip,
            }
"""
if body.count(old_headers) != 1:
    raise SystemExit('H8J expected exactly one native headers block')
body = body.replace(old_headers, new_headers, 1)

old_sid = "            sid = jsonvars['body']['sid']\n"
new_sid = """            sid = jsonvars['body']['sid']

            # G10-19H8J-FINAL-NATIVE-GXP16XX — reproduce browser session cookie contract
            cookie_parts = []
            for header_name, header_value in response.getheaders():
                if header_name.lower() == 'set-cookie':
                    cookie_pair = header_value.split(';', 1)[0].strip()
                    if cookie_pair and not cookie_pair.lower().startswith('session-identity='):
                        cookie_parts.append(cookie_pair)
            cookie_parts.append('session-identity=' + sid)
            headers['Cookie'] = '; '.join(cookie_parts)
"""
if body.count(old_sid) != 1:
    raise SystemExit('H8J expected exactly one SID assignment')
body = body.replace(old_sid, new_sid, 1)
open(dst, 'w', encoding='utf-8').write(prefix + body + suffix)
PY

  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: H8J SHA unchanged' >&2; exit 1; }
  inspect_grandstream_h8j_final_native
  echo "before_sha256=$before_sha"
  echo "after_sha256=$after_sha"
  echo 'G10-19H8J-FINAL-NATIVE-APPLY-PASS'
}

rollback_grandstream_h8j_final_native() {
  [ -f "$GRANDSTREAM_H8J_FINAL_BACKUP" ] || { echo 'ERROR: no H8J backup exists' >&2; exit 1; }
  grep -Fq '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY" || { echo 'ERROR: H8J marker absent; rollback cancelled' >&2; exit 1; }
  python3 -m py_compile "$GRANDSTREAM_H8J_FINAL_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_H8J_FINAL_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8J_FINAL_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  ! grep -Fq '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'G10-19H8J-FINAL-NATIVE-ROLLBACK-PASS'
}

commit_grandstream_h8j_final_native() {
  grep -Fq '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY" || { echo 'ERROR: H8J final patch not active' >&2; exit 1; }
  python3 -m py_compile "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8J_FINAL_BACKUP"
  echo 'final_native_patch_retained=YES'
  echo 'secret_values_logged=NO'
  echo 'G10-19H8J-FINAL-NATIVE-COMMIT-PASS'
}
'''

anchor = '\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor) != 1:
    raise SystemExit('H8J helper action anchor missing')
if 'apply_grandstream_h8j_final_native()' not in s:
    s = s.replace(anchor, funcs + anchor, 1)

case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8J helper case anchor missing')
if 'apply-grandstream-h8j-final-native)' not in s:
    s = s.replace(case_anchor, case_anchor
        + '\n  inspect-grandstream-h8j-final-native) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_h8j_final_native ;;'
        + '\n  apply-grandstream-h8j-final-native) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8j_final_native ;;'
        + '\n  rollback-grandstream-h8j-final-native) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8j_final_native ;;'
        + '\n  commit-grandstream-h8j-final-native) [ -z "$OVERLAY_ROOT" ] || usage; commit_grandstream_h8j_final_native ;;', 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8J-FINAL-HELPER-PREPARE=PASS')
