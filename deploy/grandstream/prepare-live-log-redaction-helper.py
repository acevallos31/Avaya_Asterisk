#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H8F0-GRANDSTREAM-LOG-REDACTION'

if marker in s:
    print('G10-19H8F0-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

anchor = '\n[ -n "$ACTION" ] || usage\n'
if anchor not in s:
    raise SystemExit('ERROR: helper action anchor not found')

funcs = r'''

# G10-19H8F0-GRANDSTREAM-LOG-REDACTION
inspect_grandstream_sensitive_logging() {
  local unsafe_count redaction_marker_count
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  unsafe_count="$(python3 - "$GRANDSTREAM_PY" <<'PY'
from pathlib import Path
import sys,re
s=Path(sys.argv[1]).read_text(encoding='utf-8',errors='ignore')
# Only count logging calls that interpolate encoded vars/SID. The legitimate
# payload construction urlencode(vars) must remain untouched.
count=0
for m in re.finditer(r'logging\.error\((.*?)\)\s*', s, re.S):
    block=m.group(1)
    if 'urlencode(vars)' in block or ("sid" in block and 'vars rejected by interface' in block):
        count += 1
print(count)
PY
)"
  redaction_marker_count="$(grep -Fc '# G10-19H8F0-SAFE-ERROR-LOGGING' "$GRANDSTREAM_PY" || true)"
  echo 'scope=READ_ONLY_GRANDSTREAM_SENSITIVE_LOGGING_INSPECTION'
  echo "unsafe_sensitive_error_log_count=$unsafe_count"
  echo "safe_logging_marker_count=$redaction_marker_count"
  if [ "$unsafe_count" -eq 0 ]; then
    echo 'sensitive_logging_state=SAFE'
  else
    echo 'sensitive_logging_state=UNSAFE'
  fi
  echo 'GRANDSTREAM-SENSITIVE-LOGGING-INSPECT-PASS'
}

apply_grandstream_log_redaction() {
  local backup="$STATE_DIR/Grandstream.py.pre-g10-19h8f0" tmp before_sha after_sha unsafe_before unsafe_after
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  install -d -m 0755 "$STATE_DIR"

  unsafe_before="$(python3 - "$GRANDSTREAM_PY" <<'PY'
from pathlib import Path
import sys,re
s=Path(sys.argv[1]).read_text(encoding='utf-8',errors='ignore')
count=0
for m in re.finditer(r'logging\.error\((.*?)\)\s*', s, re.S):
    b=m.group(1)
    if 'urlencode(vars)' in b or ("sid" in b and 'vars rejected by interface' in b): count += 1
print(count)
PY
)"
  if [ "$unsafe_before" -eq 0 ]; then
    inspect_grandstream_sensitive_logging
    echo 'GRANDSTREAM-LOG-REDACTION-APPLY=ALREADY_SAFE'
    return 0
  fi

  [ ! -e "$backup" ] || { echo 'ERROR: H8F0 backup already exists; refusing overwrite' >&2; exit 1; }
  tmp="$(mktemp /tmp/Grandstream.g10-19h8f0.XXXXXX.py)"
  cp -a "$GRANDSTREAM_PY" "$tmp"

  python3 - "$tmp" <<'PY'
from pathlib import Path
import sys,re
p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8')

# Replace only the two known GXP140x error log calls which previously emitted
# urlencode(vars) and the live SID. Do not modify payload construction.
pat1=re.compile(r"\s*logging\.error\('jsonvars vacio %s@%s GXP140x - vars rejected by interface - %s - %s - %s' %\s*\n\s*\(self\._vendorname, self\._ip, urlencode\(vars\), 'N/A', sid\)\)")
rep1="\n                # G10-19H8F0-SAFE-ERROR-LOGGING\n                logging.error('Endpoint %s@%s GXP140x - vars rejected by interface (unparseable response)' %\n                              (self._vendorname, self._ip))"
s,n1=pat1.subn(rep1,s,count=1)

pat2=re.compile(r"\s*logging\.error\('Endpoint %s@%s GXP140x - vars rejected by interface - %s - %s - %s' %\s*\n\s*\(self\._vendorname, self\._ip, urlencode\(vars\), jsonvars\['body'\], sid\)\)")
rep2="\n                # G10-19H8F0-SAFE-ERROR-LOGGING\n                logging.error('Endpoint %s@%s GXP140x - vars rejected by interface' %\n                              (self._vendorname, self._ip))"
s,n2=pat2.subn(rep2,s,count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit('ERROR: expected two known unsafe GXP140x logging blocks; got %d,%d' % (n1,n2))
p.write_text(s,encoding='utf-8')
PY

  python3 -m py_compile "$tmp"
  # Preserve integrated XML generation and live compatibility patches.
  grep -Fq '# G10-19H6-INTEGRATED-XML-GENERATOR' "$tmp" || { echo 'ERROR: H7 XML generator missing in candidate' >&2; rm -f "$tmp"; exit 1; }
  grep -Fq "'username': self._http_username" "$tmp" || { echo 'ERROR: G10-14 username patch missing' >&2; rm -f "$tmp"; exit 1; }
  grep -Fq "'Host': self._ip" "$tmp" || { echo 'ERROR: G10-15 Host patch missing' >&2; rm -f "$tmp"; exit 1; }
  grep -Fq "'Referer': 'http://%s/' % self._ip" "$tmp" || { echo 'ERROR: G10-15 Referer patch missing' >&2; rm -f "$tmp"; exit 1; }
  grep -Fq '# G10-19H8F0-SAFE-ERROR-LOGGING' "$tmp"

  unsafe_after="$(python3 - "$tmp" <<'PY'
from pathlib import Path
import sys,re
s=Path(sys.argv[1]).read_text(encoding='utf-8',errors='ignore')
count=0
for m in re.finditer(r'logging\.error\((.*?)\)\s*', s, re.S):
    b=m.group(1)
    if 'urlencode(vars)' in b or ("sid" in b and 'vars rejected by interface' in b): count += 1
print(count)
PY
)"
  [ "$unsafe_after" -eq 0 ] || { echo "ERROR: unsafe logging remains count=$unsafe_after" >&2; rm -f "$tmp"; exit 1; }

  cp -a "$GRANDSTREAM_PY" "$backup"
  chmod 0600 "$backup"
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  python3 -m py_compile "$GRANDSTREAM_PY"
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: live SHA unchanged after H8F0 apply' >&2; exit 1; }
  inspect_grandstream_sensitive_logging
  echo "unsafe_before=$unsafe_before"
  echo "unsafe_after=$unsafe_after"
  echo 'backup_state=PRESENT_SECURE'
  echo 'GRANDSTREAM-LOG-REDACTION-APPLY-PASS'
}

rollback_grandstream_log_redaction() {
  local backup="$STATE_DIR/Grandstream.py.pre-g10-19h8f0"
  [ -f "$backup" ] || { echo 'ERROR: H8F0 rollback backup absent' >&2; exit 1; }
  python3 -m py_compile "$backup"
  install -o root -g root -m 0644 "$backup" "$GRANDSTREAM_PY"
  rm -f "$backup" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  echo 'GRANDSTREAM-LOG-REDACTION-ROLLBACK-PASS'
}
'''

s=s.replace(anchor,funcs+anchor,1)
case_anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: helper case anchor not found')
new=case_anchor+r'''
  inspect-grandstream-sensitive-logging) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_sensitive_logging ;;
  apply-grandstream-log-redaction) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_log_redaction ;;
  rollback-grandstream-log-redaction) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_log_redaction ;;'''
s=s.replace(case_anchor,new,1)
p.write_text(s,encoding='utf-8')
print('G10-19H8F0-HELPER-PREPARE=PASS')
