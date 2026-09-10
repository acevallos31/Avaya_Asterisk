#!/usr/bin/env python3
"""Prepare restricted helper actions for G10-19H8H2.

H8H1 proved, without exposing values, that on GXP1625 firmware 1.0.7.70:
- /cgi-bin/dologin returns a SID in JSON;
- session-role is delivered as Set-Cookie;
- session-identity is NOT delivered as Set-Cookie;
- the browser-created session-identity cookie equals that login SID.

This preparer only modifies the checked-out privileged-helper source. The helper
then applies/inspects/rolls back one targeted live Grandstream.py change.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H8H2-SESSION-IDENTITY'

if 'GRANDSTREAM_H8H2_PATCH_BACKUP=' not in s:
    anchor = 'GRANDSTREAM_LOGIN_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-14"\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2: backup anchor not found exactly once')
    s = s.replace(
        anchor,
        anchor + 'GRANDSTREAM_H8H2_PATCH_BACKUP="$STATE_DIR/Grandstream.py.pre-g10-19h8h2"\n',
        1,
    )

funcs = r'''

inspect_grandstream_h8h2_session_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  local username_count host_count referer_count marker_count synth_count cookie_count file_sha
  username_count="$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  marker_count="$(grep -Fc '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY" || true)"
  synth_count="$(grep -Fc "cookie_parts.append('session-identity=' + sid)" "$GRANDSTREAM_PY" || true)"
  cookie_count="$(grep -Fc "headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY" || true)"
  file_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  echo 'scope=GRANDSTREAM_H8H2_SESSION_PATCH_AUDIT'
  echo 'secret_values_logged=NO'
  echo "grandstream_py_sha256=$file_sha"
  echo "username_payload_line_count=$username_count"
  echo "host_header_line_count=$host_count"
  echo "referer_header_line_count=$referer_count"
  echo "h8h2_marker_count=$marker_count"
  echo "session_identity_synth_line_count=$synth_count"
  echo "cookie_header_line_count=$cookie_count"
  if [ -f "$GRANDSTREAM_H8H2_PATCH_BACKUP" ]; then
    echo 'h8h2_backup_present=YES'
  else
    echo 'h8h2_backup_present=NO'
  fi
  if [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] && [ "$marker_count" -eq 0 ] && [ "$synth_count" -eq 0 ]; then
    echo 'h8h2_patch_state=READY'
  elif [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] && [ "$marker_count" -eq 1 ] && [ "$synth_count" -eq 1 ] && [ "$cookie_count" -ge 1 ]; then
    echo 'h8h2_patch_state=PATCHED'
  else
    echo 'h8h2_patch_state=UNEXPECTED'
    return 1
  fi
  echo 'GRANDSTREAM-H8H2-SESSION-PATCH-INSPECT-PASS'
}

apply_grandstream_h8h2_session_patch() {
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  install -d -o root -g root -m 0700 "$STATE_DIR"
  local username_count host_count referer_count marker_count before_sha after_sha tmp
  username_count="$(grep -Fxc "                'username': self._http_username," "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fxc "                'Host': self._ip," "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fxc "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY" || true)"
  marker_count="$(grep -Fc '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY" || true)"

  if [ "$marker_count" -eq 1 ]; then
    echo 'GRANDSTREAM-H8H2-SESSION-PATCH-ALREADY-PRESENT'
    inspect_grandstream_h8h2_session_patch
    return 0
  fi

  [ "$username_count" -eq 1 ] && [ "$host_count" -eq 1 ] && [ "$referer_count" -eq 1 ] || {
    echo 'ERROR: G10-14/G10-15 live baseline not present; H8H2 apply cancelled.' >&2
    exit 1
  }
  [ ! -e "$GRANDSTREAM_H8H2_PATCH_BACKUP" ] || {
    echo 'ERROR: H8H2 backup already exists while patch marker is absent; manual review required.' >&2
    exit 1
  }

  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  cp -a "$GRANDSTREAM_PY" "$GRANDSTREAM_H8H2_PATCH_BACKUP"
  chmod 0600 "$GRANDSTREAM_H8H2_PATCH_BACKUP"
  tmp="$(mktemp "$STATE_DIR/Grandstream.py.h8h2.XXXXXX")"

  python3 - "$GRANDSTREAM_PY" "$tmp" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, 'r', encoding='utf-8').read()
anchor = "            sid = jsonvars['body']['sid']\n"
if text.count(anchor) != 1:
    raise SystemExit('H8H2 expected exactly one GXP140x SID assignment')
block = """            sid = jsonvars['body']['sid']

            # G10-19H8H2-SESSION-IDENTITY
            # GXP16xx 1.0.7.x web UI receives session-role from Set-Cookie but
            # creates session-identity client-side with the JSON login SID.
            # Reproduce that browser session contract without logging values.
            cookie_parts = []
            for header_name, header_value in response.getheaders():
                if header_name.lower() == 'set-cookie':
                    cookie_pair = header_value.split(';', 1)[0].strip()
                    if cookie_pair and not cookie_pair.lower().startswith('session-identity='):
                        cookie_parts.append(cookie_pair)
            cookie_parts.append('session-identity=' + sid)
            headers['Cookie'] = '; '.join(cookie_parts)
"""
text = text.replace(anchor, block, 1)
open(dst, 'w', encoding='utf-8').write(text)
PY

  python3 -m py_compile "$tmp"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: H8H2 SHA unchanged.' >&2; exit 1; }
  grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY"
  grep -Fq "cookie_parts.append('session-identity=' + sid)" "$GRANDSTREAM_PY"
  grep -Fq "headers['Cookie'] = '; '.join(cookie_parts)" "$GRANDSTREAM_PY"
  echo "before_sha256=$before_sha"
  echo "after_sha256=$after_sha"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2-SESSION-PATCH-APPLY-PASS'
}

rollback_grandstream_h8h2_session_patch() {
  [ -f "$GRANDSTREAM_H8H2_PATCH_BACKUP" ] || { echo 'ERROR: no H8H2 backup exists.' >&2; exit 1; }
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY" || {
    echo 'ERROR: live file does not contain H8H2 marker; rollback cancelled.' >&2
    exit 1
  }
  python3 -m py_compile "$GRANDSTREAM_H8H2_PATCH_BACKUP"
  install -o root -g root -m 0644 "$GRANDSTREAM_H8H2_PATCH_BACKUP" "$GRANDSTREAM_PY"
  rm -f "$GRANDSTREAM_H8H2_PATCH_BACKUP" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  ! grep -Fq '# G10-19H8H2-SESSION-IDENTITY' "$GRANDSTREAM_PY"
  grep -Fq "                'username': self._http_username," "$GRANDSTREAM_PY"
  grep -Fq "                'Host': self._ip," "$GRANDSTREAM_PY"
  grep -Fq "                'Referer': 'http://%s/' % self._ip," "$GRANDSTREAM_PY"
  echo 'secret_values_logged=NO'
  echo 'GRANDSTREAM-H8H2-SESSION-PATCH-ROLLBACK-PASS'
}
'''

if 'inspect_grandstream_h8h2_session_patch()' not in s:
    anchor = '\n[ -n "$ACTION" ] || usage\n'
    if s.count(anchor) != 1:
        raise SystemExit('H8H2: helper action anchor not found exactly once')
    s = s.replace(anchor, funcs + anchor, 1)

if 'inspect-grandstream-h8h2-session-patch)' not in s:
    case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;\n'
    if s.count(case_anchor) != 1:
        raise SystemExit('H8H2: helper case anchor not found exactly once')
    cases = (
        case_anchor
        + '  inspect-grandstream-h8h2-session-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_h8h2_session_patch ;;\n'
        + '  apply-grandstream-h8h2-session-patch) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_h8h2_session_patch ;;\n'
        + '  rollback-grandstream-h8h2-session-patch) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_h8h2_session_patch ;;\n'
    )
    s = s.replace(case_anchor, cases, 1)

p.write_text(s, encoding='utf-8')
print('G10-19H8H2-HELPER-PREPARE=PASS')
