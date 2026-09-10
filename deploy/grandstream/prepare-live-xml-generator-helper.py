#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H7-LIVE-XML-GENERATOR-HELPER'

if marker in s:
    print('G10-19H7-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

anchor = '\n[ -n "$ACTION" ] || usage\n'
if anchor not in s:
    raise SystemExit('ERROR: helper action anchor not found')

funcs = r'''

# G10-19H7-LIVE-XML-GENERATOR-HELPER
inspect_grandstream_xml_generator() {
  local marker_count xml_write_count binary_write_count login_user_count host_count referer_count
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  marker_count="$(grep -Fc '# G10-19H6-INTEGRATED-XML-GENERATOR' "$GRANDSTREAM_PY" || true)"
  xml_write_count="$(grep -Fc "self._writeContent(sConfigPath + '.xml', self._encodeGrandstreamXmlConfig(vars))" "$GRANDSTREAM_PY" || true)"
  binary_write_count="$(grep -Fc 'self._writeContent(sConfigPath, self._encodeGrandstreamConfig(vars))' "$GRANDSTREAM_PY" || true)"
  login_user_count="$(grep -Fc "'username': self._http_username" "$GRANDSTREAM_PY" || true)"
  host_count="$(grep -Fc "'Host': self._ip" "$GRANDSTREAM_PY" || true)"
  referer_count="$(grep -Fc "'Referer': 'http://%s/' % self._ip" "$GRANDSTREAM_PY" || true)"
  echo 'scope=READ_ONLY_LIVE_GRANDSTREAM_XML_GENERATOR_INSPECTION'
  echo "xml_generator_marker_count=$marker_count"
  echo "binary_generation_count=$binary_write_count"
  echo "xml_generation_count=$xml_write_count"
  echo "g10_14_username_patch_present=$([ "$login_user_count" -ge 1 ] && echo YES || echo NO)"
  echo "g10_15_host_patch_present=$([ "$host_count" -ge 1 ] && echo YES || echo NO)"
  echo "g10_15_referer_patch_present=$([ "$referer_count" -ge 1 ] && echo YES || echo NO)"
  if [ "$marker_count" -eq 1 ] && [ "$xml_write_count" -eq 1 ] && [ "$binary_write_count" -eq 1 ]; then
    python3 -m py_compile "$GRANDSTREAM_PY"
    echo 'live_xml_generator_state=PRESENT_VALID'
  elif [ "$marker_count" -eq 0 ] && [ "$xml_write_count" -eq 0 ] && [ "$binary_write_count" -eq 1 ]; then
    echo 'live_xml_generator_state=ABSENT'
  else
    echo 'live_xml_generator_state=INCONSISTENT'
    return 1
  fi
  echo 'GRANDSTREAM-XML-GENERATOR-INSPECT-PASS'
}

apply_grandstream_xml_generator() {
  local backup="$STATE_DIR/Grandstream.py.pre-g10-19h7" tmp before_sha after_sha
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  install -d -m 0755 "$STATE_DIR"

  if grep -Fq '# G10-19H6-INTEGRATED-XML-GENERATOR' "$GRANDSTREAM_PY"; then
    inspect_grandstream_xml_generator
    echo 'GRANDSTREAM-XML-GENERATOR-APPLY=ALREADY_PRESENT'
    return 0
  fi

  # Preserve the already validated G10-14/G10-15 login compatibility patches.
  grep -Fq "'username': self._http_username" "$GRANDSTREAM_PY" || { echo 'ERROR: G10-14 username patch missing; refusing H7 apply' >&2; exit 1; }
  grep -Fq "'Host': self._ip" "$GRANDSTREAM_PY" || { echo 'ERROR: G10-15 Host patch missing; refusing H7 apply' >&2; exit 1; }
  grep -Fq "'Referer': 'http://%s/' % self._ip" "$GRANDSTREAM_PY" || { echo 'ERROR: G10-15 Referer patch missing; refusing H7 apply' >&2; exit 1; }

  tmp="$(mktemp /tmp/Grandstream.g10-19h7.XXXXXX.py)"
  cp -a "$GRANDSTREAM_PY" "$tmp"

  python3 - "$tmp" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
marker = '# G10-19H6-INTEGRATED-XML-GENERATOR'
if marker in s:
    raise SystemExit(0)

import_anchor = 'import http.client\n'
if s.count(import_anchor) != 1:
    raise SystemExit('ERROR: expected exactly one http.client import anchor')
s = s.replace(import_anchor, import_anchor + 'import xml.etree.ElementTree as ET\n', 1)

write_anchor = "            self._writeContent(sConfigPath, self._encodeGrandstreamConfig(vars))\n"
if s.count(write_anchor) != 1:
    raise SystemExit('ERROR: expected exactly one binary write anchor')
s = s.replace(write_anchor, write_anchor + "            self._writeContent(sConfigPath + '.xml', self._encodeGrandstreamXmlConfig(vars))\n", 1)

method_anchor = '    def _encodeGrandstreamConfig(self, vars):\n'
if s.count(method_anchor) != 1:
    raise SystemExit('ERROR: expected exactly one encoder anchor')
method = r'''    # G10-19H6-INTEGRATED-XML-GENERATOR
    def _encodeGrandstreamXmlConfig(self, vars):
        """Encode the same P-value map used by the legacy binary cfg as Grandstream XML."""
        root = ET.Element('gs_provision', {'version': '1'})
        ET.SubElement(root, 'mac').text = self._mac.replace(':', '').lower()
        config = ET.SubElement(root, 'config', {'version': '1'})

        def sort_key(key):
            if key.startswith('P') and key[1:].isdigit():
                return (0, int(key[1:]))
            return (1, key)

        for key in sorted(vars.keys(), key=sort_key):
            if key.startswith('P') and key[1:].isdigit():
                value = vars[key]
                ET.SubElement(config, key).text = '' if value is None else str(value)

        return ET.tostring(root, encoding='UTF-8', xml_declaration=True)

'''
s = s.replace(method_anchor, method + method_anchor, 1)
p.write_text(s, encoding='utf-8')
PY

  python3 -m py_compile "$tmp"
  grep -Fq '# G10-19H6-INTEGRATED-XML-GENERATOR' "$tmp"
  grep -Fq "self._writeContent(sConfigPath + '.xml', self._encodeGrandstreamXmlConfig(vars))" "$tmp"
  grep -Fq "'username': self._http_username" "$tmp"
  grep -Fq "'Host': self._ip" "$tmp"
  grep -Fq "'Referer': 'http://%s/' % self._ip" "$tmp"

  [ ! -e "$backup" ] || { echo "ERROR: backup H7 ya existe; refusing to overwrite rollback point" >&2; rm -f "$tmp"; exit 1; }
  cp -a "$GRANDSTREAM_PY" "$backup"
  chmod 0600 "$backup"
  before_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  install -o root -g root -m 0644 "$tmp" "$GRANDSTREAM_PY"
  rm -f "$tmp" "${GRANDSTREAM_PY}c" 2>/dev/null || true
  after_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  [ "$before_sha" != "$after_sha" ] || { echo 'ERROR: live SHA unchanged after H7 apply' >&2; exit 1; }

  inspect_grandstream_xml_generator
  echo "before_sha256=$before_sha"
  echo "after_sha256=$after_sha"
  echo 'backup_state=PRESENT_SECURE'
  echo 'GRANDSTREAM-XML-GENERATOR-APPLY-PASS'
}

rollback_grandstream_xml_generator() {
  local backup="$STATE_DIR/Grandstream.py.pre-g10-19h7" restored_sha
  [ -f "$backup" ] || { echo 'ERROR: H7 rollback backup absent' >&2; exit 1; }
  [ -f "$GRANDSTREAM_PY" ] || { echo "ERROR: no existe $GRANDSTREAM_PY" >&2; exit 1; }
  grep -Fq '# G10-19H6-INTEGRATED-XML-GENERATOR' "$GRANDSTREAM_PY" || { echo 'ERROR: H7 marker absent on live file; rollback cancelled' >&2; exit 1; }
  python3 -m py_compile "$backup"
  install -o root -g root -m 0644 "$backup" "$GRANDSTREAM_PY"
  rm -f "${GRANDSTREAM_PY}c" 2>/dev/null || true
  restored_sha="$(sha256sum "$GRANDSTREAM_PY" | awk '{print $1}')"
  rm -f "$backup"
  echo "restored_sha256=$restored_sha"
  echo 'GRANDSTREAM-XML-GENERATOR-ROLLBACK-PASS'
}
'''

s = s.replace(anchor, funcs + anchor, 1)

case_anchor = '  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: helper case anchor not found')
new_cases = case_anchor + r'''
  inspect-grandstream-xml-generator) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_xml_generator ;;
  apply-grandstream-xml-generator) [ -z "$OVERLAY_ROOT" ] || usage; apply_grandstream_xml_generator ;;
  rollback-grandstream-xml-generator) [ -z "$OVERLAY_ROOT" ] || usage; rollback_grandstream_xml_generator ;;'''
s = s.replace(case_anchor, new_cases, 1)

p.write_text(s, encoding='utf-8')
print('G10-19H7-HELPER-PREPARE=PASS')
