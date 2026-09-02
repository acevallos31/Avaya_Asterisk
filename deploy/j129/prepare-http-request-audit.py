#!/usr/bin/env python3
from pathlib import Path

path = Path('deploy/j129/avaya-j129-lab-deploy')
text = path.read_text(encoding='utf-8')
old = "  local phone_ip='192.168.1.171' found=0 log needle tmp\n"
new = "  local defaults_file phone_ip found=0 log needle tmp\n  defaults_file=\"$(make_db_defaults_file)\"\n  phone_ip=\"$(mysql_scalar \"$defaults_file\" \"SELECT e.last_known_ipv4 FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' LIMIT 1;\")\"\n  rm -f \"$defaults_file\"\n  [ -n \"$phone_ip\" ] || { echo 'ERROR: J129 sin last_known_ipv4 en Endpoint Configurator' >&2; exit 1; }\n"
if old not in text:
    raise SystemExit('No se encontró el bloque HTTP esperado para parchear')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('HTTP-REQUEST-AUDIT-PREPARE-PASS')
