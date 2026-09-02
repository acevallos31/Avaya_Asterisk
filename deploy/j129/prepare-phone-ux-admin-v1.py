#!/usr/bin/env python3
from pathlib import Path

HELPER = Path('deploy/j129/avaya-j129-lab-deploy')
text = HELPER.read_text()

if 'apply-phone-ux-v1|apply-phone-ux-v2)' in text:
    print('PHONE-UX-PREPARE-ALREADY-PRESENT')
    raise SystemExit(0)

marker = 'case "$ACTION" in\n'
if marker not in text:
    raise SystemExit('No se encontro case "$ACTION" in en helper')

block = r'''  apply-phone-ux-v1|apply-phone-ux-v2)
    TPL=/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
    BACKUP=/var/lib/avaya-j129-lab/Avaya_global_SIP.tpl.pre-phone-ux-v1
    [ -f "$TPL" ] || { echo "ERROR: no existe $TPL" >&2; exit 1; }
    install -d -m 0755 /var/lib/avaya-j129-lab
    [ -f "$BACKUP" ] || cp -a "$TPL" "$BACKUP"

    python3 - "$TPL" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
params = {
    'PROCSTAT': '1',
    'PROVIDE_OPTIONS_SCREEN': '1',
    'PROVIDE_NETWORKINFO_SCREEN': '1',
    'PROVIDE_LOGOUT': '1',
    'ENTRYNAME': 'Briam',
}
lines = s.splitlines()
for key, value in params.items():
    prefix = 'SET ' + key + ' '
    lines = [line for line in lines if not line.strip().startswith(prefix)]
    lines.append('SET %s %s' % (key, value))
p.write_text('\n'.join(lines) + '\n')
PY

    defaults_file="$(make_db_defaults_file)"
    trap 'rm -f "$defaults_file"' RETURN EXIT
    target_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D';")"
    [ "$target_count" = "1" ] || { echo "ERROR: se esperaba exactamente un J129 objetivo y se encontraron $target_count" >&2; exit 1; }
    target_id="$(mysql_scalar "$defaults_file" "SELECT e.id FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' LIMIT 1;")"
    selected_other="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE selected=1 AND id<>${target_id};")"
    [ "$selected_other" = "0" ] || { echo "ERROR: hay otros endpoints seleccionados; se aborta" >&2; exit 1; }

    mysql --defaults-extra-file="$defaults_file" endpointconfig -e "UPDATE endpoint SET selected=1 WHERE id=${target_id};"
    echo "PHONE_UX_SELECTED_ENDPOINT=${target_id}"
    /usr/bin/issabel-endpointconfig --applyconfig
    selected_after="$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${target_id};")"
    [ "$selected_after" = "0" ] || { echo 'ERROR: Issabel no limpio selected del J129' >&2; exit 1; }
    echo 'PHONE_UX_SELECTED_CLEARED=YES'
    rm -f "$defaults_file"; trap - RETURN EXIT
    echo 'J129-PHONE-UX-V2-APPLY-PASS'
    ;;
  phone-ux-sip-ok)
    OUT=$(asterisk -rx 'sip show peer 200' 2>&1)
    echo "$OUT" | grep -Eq 'Status[[:space:]]*: OK' || { echo 'SIP_STATUS=NOT_OK account=200' >&2; exit 1; }
    echo 'SIP_STATUS=OK account=200'
    ;;
'''

text = text.replace(marker, marker + block, 1)
HELPER.write_text(text)
print('PHONE-UX-PREPARE-PASS')
