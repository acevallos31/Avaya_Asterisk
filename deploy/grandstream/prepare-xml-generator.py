#!/usr/bin/env python3
from pathlib import Path

p = Path('usr/share/issabel/endpoint-classes/class/issabel/vendor/Grandstream.py')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H6-INTEGRATED-XML-GENERATOR'

if marker in s:
    print('G10-19H6-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

import_anchor = 'import http.client\n'
if import_anchor not in s:
    raise SystemExit('ERROR: import anchor not found')
s = s.replace(import_anchor, import_anchor + 'import xml.etree.ElementTree as ET\n', 1)

write_anchor = "            self._writeContent(sConfigPath, self._encodeGrandstreamConfig(vars))\n"
if write_anchor not in s:
    raise SystemExit('ERROR: binary write anchor not found')
s = s.replace(write_anchor, write_anchor + "            self._writeContent(sConfigPath + '.xml', self._encodeGrandstreamXmlConfig(vars))\n", 1)

method_anchor = '    def _encodeGrandstreamConfig(self, vars):\n'
if method_anchor not in s:
    raise SystemExit('ERROR: encoder anchor not found')
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
print('G10-19H6-PREPARE=PASS')
