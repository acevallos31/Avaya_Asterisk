from pathlib import Path

helper = Path('deploy/j129/avaya-j129-lab-deploy')
text = helper.read_text()

old_decl = "local defaults_file account expected_ip='192.168.1.171' sip_out pjsip_out registered=0"
new_decl = "local defaults_file account expected_ip sip_out pjsip_out registered=0"

old_account = "account=\"$(mysql_scalar \"$defaults_file\" \"SELECT ea.account FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model JOIN endpoint_account ea ON ea.id_endpoint=e.id WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' ORDER BY ea.priority LIMIT 1;\")\"\n  [ -n \"$account\" ] || { echo 'ERROR: J129 no tiene cuenta asignada en Endpoint Configurator' >&2; exit 1; }"
new_account = "account=\"$(mysql_scalar \"$defaults_file\" \"SELECT ea.account FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model JOIN endpoint_account ea ON ea.id_endpoint=e.id WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' ORDER BY ea.priority LIMIT 1;\")\"\n  expected_ip=\"$(mysql_scalar \"$defaults_file\" \"SELECT e.last_known_ipv4 FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' LIMIT 1;\")\"\n  [ -n \"$account\" ] || { echo 'ERROR: J129 no tiene cuenta asignada en Endpoint Configurator' >&2; exit 1; }\n  [ -n \"$expected_ip\" ] || { echo 'ERROR: J129 no tiene last_known_ipv4 en Endpoint Configurator' >&2; exit 1; }"

if old_decl not in text:
    raise SystemExit('No se encontro declaracion esperada de inspect-sip-registration')
if old_account not in text:
    raise SystemExit('No se encontro bloque esperado de cuenta SIP')

text = text.replace(old_decl, new_decl, 1)
text = text.replace(old_account, new_account, 1)
helper.write_text(text)
print('SIP-REGISTRATION-AUDIT-PREPARE-PASS')
