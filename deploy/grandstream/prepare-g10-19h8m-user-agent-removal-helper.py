#!/usr/bin/env python3
"""Prepare a reversible migration from H8J's curl-like User-Agent.

H8L proved that the validated GXP1625 login succeeds without an explicit
User-Agent. This helper changes only the retained live H8J implementation and
never logs credentials, SID values, cookies or submitted P-values.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'GRANDSTREAM_H8M_UA_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8M backup anchor missing')
    s = s.replace(anchor, anchor + 'GRANDSTREAM_H8M_UA_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8m-ua"\n', 1)

funcs = r'''

inspect_grandstream_h8m_user_agent() {
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: Grandstream.py missing' >&2; exit 1; }
  local final_count accept_count ua_count sid_count cookie_count
  final_count="$(grep -Fc '# G10-19H8J-FINAL-NATIVE-GXP16XX' "$GRANDSTREAM_PY" || true)"
  accept_count="$(grep -Fc "'Accept': '*/*'" "$GRANDSTREAM_PY" || true)"
  ua_count="$(grep -Fc "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY" || true)"
  sid_count="$(grep -Fc "cookie_parts.append('session-identity=' + sid)" "$GRANDSTREAM_PY" || true)"
  cookie_count="$(grep -Fc "headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY" || true)"
  echo 'scope=G10_19H8M_MINIMAL_NATIVE_AUDIT'
  echo 'secret_values_logged=NO'
  echo "final_marker_count=$final_count"
  echo "accept_header_count=$accept_count"
  echo "curl_user_agent_count=$ua_count"
  echo "session_identity_synth_count=$sid_count"
  echo "cookie_header_count=$cookie_count"
  if [ "$final_count" -ge 2 ] && [ "$accept_count" -ge 1 ] && [ "$ua_count" -eq 1 ] && [ "$sid_count" -eq 1 ] && [ "$cookie_count" -ge 1 ]; then
    echo 'h8m_state=READY'
  elif [ "$final_count" -ge 2 ] && [ "$accept_count" -ge 1 ] && [ "$ua_count" -eq 0 ] && [ "$sid_count" -eq 1 ] && [ "$cookie_count" -ge 1 ]; then
    echo 'h8m_state=PATCHED'
  else
    echo 'h8m_state=UNEXPECTED'
    return 1
  fi
  echo 'G10-19H8M-UA-INSPECT-PASS'
}

apply_grandstream_h8m_user_agent() {
  inspect_grandstream_h8m_user_agent
  if ! grep -Fq "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY"; then
    echo 'G10-19H8M-UA-APPLY=ALREADY_PRESENT'
    return 0
  fi
  [ ! -e "$GRANDSTREAM_H8M_UA_BACKUP" ] || { echo 'ERROR: H8M backup already exists' >&2; exit 1; }
  install -d -o root -g root -m 0700 "$STATE_DIR"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8M_UA_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8M_UA_BACKUP"
  local tmp before_sha after_sha
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8m.XXXXXX")"
  python3 -B - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
line = "                'User-Agent': 'curl/8.14.1',\n"
if text.count(line) != 1:
    raise SystemExit('H8M expected exactly one curl-like User-Agent line')
open(dst, 'w', encoding='utf-8').write(text.replace(line, '', 1))
PY
  PYTHONDONTWRITEBYTECODE=1 python3 -B -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: H8M SHA unchanged' >&2; exit 1; }
  inspect_grandstream_h8m_user_agent
  echo "before_sha256=$before_sha"
  echo "after_sha256=$after_sha"
  echo 'G10-19H8M-UA-APPLY-PASS'
}

rollback_grandstream_h8m_user_agent() {
  if [ ! -f "$GRANDSTREAM_H8M_UA_BACKUP" ]; then
    echo 'G10-19H8M-UA-ROLLBACK=ALREADY_CLEAN'
    return 0
  fi
  [ "$(grep -Fc "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY" || true)" -eq 0 ] || { echo 'ERROR: H8M live state is not patched' >&2; exit 1; }
  PYTHONDONTWRITEBYTECODE=1 python3 -B -m py_compile "$GRANDSTREAM_H8M_UA_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_H8M_UA_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8M_UA_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  grep -Fq "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'G10-19H8M-UA-ROLLBACK-PASS'
}

commit_grandstream_h8m_user_agent() {
  [ -f "$GRANDSTREAM_H8M_UA_BACKUP" ] || { echo 'ERROR: H8M backup missing' >&2; exit 1; }
  [ "$(grep -Fc "'User-Agent': 'curl/8.14.1'" "$GRANDSTREAM_PY" || true)" -eq 0 ] || { echo 'ERROR: curl-like User-Agent still active' >&2; exit 1; }
  PYTHONDONTWRITEBYTECODE=1 python3 -B -m py_compile "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8M_UA_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  echo 'minimal_native_patch_retained=YES'
  echo 'secret_values_logged=NO'
  echo 'G10-19H8M-UA-COMMIT-PASS'
}
'''

anchor = '\n[ -n "$ACTION" ] || usage\n'
if s.count(anchor) != 1:
    raise SystemExit('H8M action anchor missing')
if 'apply_grandstream_h8m_user_agent()' not in s:
    s = s.replace(anchor, funcs + anchor, 1)

case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('H8M case anchor missing')
if 'apply-grandstream-h8m-user-agent)' not in s:
    s = s.replace(case_anchor, case_anchor
        + '\n  inspect-grandstream-h8m-user-agent) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_h8m_user_agent ;;'
        + '\n  apply-grandstream-h8m-user-agent) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8m_user_agent ;;'
        + '\n  rollback-grandstream-h8m-user-agent) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8m_user_agent ;;'
        + '\n  commit-grandstream-h8m-user-agent) [ -z "$OVERLAY_ROOT" ] || usage; commit_grandstream_h8m_user_agent ;;', 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8M-HELPER-PREPARE=PASS')
