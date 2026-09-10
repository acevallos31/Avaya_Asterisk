#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H8F2-PY36-XML-COMPAT'
if marker in s:
    print('G10-19H8F2-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)
anchor = '\n[ -n "$ACTION" ] || usage\n'
if anchor not in s:
    raise SystemExit('ERROR: helper action anchor missing')

func = r'''

# G10-19H8F2-PY36-XML-COMPAT
apply_grandstream_py36_xml_compat() {
  local backup="$STATE_DIR/Grandstream.py.pre-g10-19h8f2" tmp before_sha after_sha
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: live Grandstream.py missing' >&2; exit 1; }
  grep -Fq '# G10-19H6-INTEGRATED-XML-GENERATOR' "$GRANDSTREAM_PY" || { echo 'ERROR: integrated XML generator missing' >&2; exit 1; }
  grep -Fq '# G10-19H8F0-SAFE-ERROR-LOGGING' "$GRANDSTREAM_PY" || { echo 'ERROR: safe logging patch missing' >&2; exit 1; }

  if grep -Fq '# G10-19H8F2-PY36-SERIALIZER' "$GRANDSTREAM_PY"; then
    python3 -m py_compile "$GRANDSTREAM_PY"
    echo 'py36_xml_serializer_state=ALREADY_PRESENT'
    echo 'GRANDSTREAM-PY36-XML-COMPAT-APPLY=ALREADY_PRESENT'
    return 0
  fi

  [ ! -e "$backup" ] || { echo 'ERROR: H8F2 backup already exists; refusing overwrite' >&2; exit 1; }
  tmp="$(mktemp /tmp/Grandstream.g10-19h8f2.XXXXXX.py)"
  cp -a "$GRANDSTREAM_PY" "$tmp"
  python3 - "$tmp" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8')
old="        return ET.tostring(root, encoding='UTF-8', xml_declaration=True)"
new="""        # G10-19H8F2-PY36-SERIALIZER
        # Python 3.6 ElementTree.tostring() does not accept xml_declaration.
        # ElementTree.write() does, so serialize through BytesIO for Issabel 5.
        import io
        output = io.BytesIO()
        ET.ElementTree(root).write(output, encoding='UTF-8', xml_declaration=True)
        return output.getvalue()"""
if s.count(old) != 1:
    raise SystemExit('ERROR: expected exactly one Python-incompatible ET.tostring call')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
PY
  python3 -m py_compile "$tmp"
  grep -Fq '# G10-19H8F2-PY36-SERIALIZER' "$tmp"
  grep -Fq '# G10-19H8F0-SAFE-ERROR-LOGGING' "$tmp"
  grep -Fq "'username': self._http_username" "$tmp"
  grep -Fq "'Host': self._ip" "$tmp"
  grep -Fq "'Referer': 'http://%s/' % self._ip" "$tmp"

  cp -a "$GRANDSTREAM_PY" "$backup"; chmod 0600 "$backup"
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  python3 -m py_compile "$GRANDSTREAM_PY"
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: H8F2 live SHA unchanged' >&2; exit 1; }

  # Synthetic, non-secret runtime probe on the actual live module.
  python3 - <<'PY'
import sys, xml.etree.ElementTree as ET
sys.path.insert(0,'/usr/share/issabel/endpoint-classes/class')
from issabel.vendor.Grandstream import Endpoint
e=Endpoint(None,None,'192.0.2.1','192.0.2.2','C0:74:AD:E8:66:09')
out=e._encodeGrandstreamXmlConfig({'P35':'TEST202','P47':'192.0.2.10','gnkey':'TEST'})
assert isinstance(out,(bytes,bytearray))
r=ET.fromstring(out)
v={c.tag:(c.text or '') for c in r.find('config')}
assert r.tag=='gs_provision'
assert v.get('P35')=='TEST202'
assert 'gnkey' not in v
print('synthetic_runtime_encoder_probe=PASS')
PY
  echo 'python36_compatibility=PASS'
  echo 'backup_state=PRESENT_SECURE'
  echo 'GRANDSTREAM-PY36-XML-COMPAT-APPLY-PASS'
}

rollback_grandstream_py36_xml_compat() {
  local backup="$STATE_DIR/Grandstream.py.pre-g10-19h8f2"
  [ -f "$backup" ] || { echo 'ERROR: H8F2 backup missing' >&2; exit 1; }
  python3 -m py_compile "$backup"
  install -o root -g root -m 0644 "$backup" "$GRANDSTREAM_PY"
  rm -f "$backup" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  echo 'GRANDSTREAM-PY36-XML-COMPAT-ROLLBACK-PASS'
}
'''
s=s.replace(anchor,func+anchor,1)
case_anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: helper case anchor missing')
s=s.replace(case_anchor,case_anchor+'\n  apply-grandstream-py36-xml-compat) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_py36_xml_compat ;;\n  rollback-grandstream-py36-xml-compat) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_py36_xml_compat ;;',1)
p.write_text(s,encoding='utf-8')
print('G10-19H8F2-HELPER-PREPARE=PASS')
