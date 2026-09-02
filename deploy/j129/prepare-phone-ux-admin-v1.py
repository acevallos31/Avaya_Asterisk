#!/usr/bin/env python3
from pathlib import Path

HELPER = Path('deploy/j129/avaya-j129-lab-deploy')
text = HELPER.read_text()

if 'apply-phone-ux-v1)' in text:
    print('PHONE-UX-PREPARE-ALREADY-PRESENT')
    raise SystemExit(0)

marker = 'case "$ACTION" in\n'
if marker not in text:
    raise SystemExit('No se encontro case "$ACTION" in en helper')

block = r'''  apply-phone-ux-v1)
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

    # Seleccion controlada: solo el J129 LAB puede quedar seleccionado.
    python3 - <<'PY'
import sqlite3
DB='/var/www/db/endpointconfig.db'
con=sqlite3.connect(DB)
cur=con.cursor()
rows=cur.execute("SELECT id, mac_address, ip_address, selected FROM endpoint WHERE selected=1").fetchall()
foreign=[r for r in rows if (r[1] or '').lower().replace(':','') != 'c81fea9b650d']
if foreign:
    raise SystemExit('ERROR: hay otros endpoints seleccionados: %r' % (foreign,))
target=cur.execute("SELECT id, mac_address, ip_address FROM endpoint WHERE lower(replace(mac_address,':',''))='c81fea9b650d'").fetchall()
if len(target) != 1:
    raise SystemExit('ERROR: se esperaba exactamente un J129 LAB y se obtuvo %d' % len(target))
cur.execute('UPDATE endpoint SET selected=1 WHERE id=?', (target[0][0],))
con.commit()
print('PHONE_UX_SELECTED_ENDPOINT=%s ip=%s' % (target[0][0], target[0][2]))
PY

    /usr/bin/issabel-endpointconfig --applyconfig

    python3 - <<'PY'
import sqlite3
DB='/var/www/db/endpointconfig.db'
con=sqlite3.connect(DB)
cur=con.cursor()
row=cur.execute("SELECT selected FROM endpoint WHERE lower(replace(mac_address,':',''))='c81fea9b650d'").fetchone()
if row is None or row[0] != 0:
    raise SystemExit('ERROR: Issabel no limpio selected del J129')
print('PHONE_UX_SELECTED_CLEARED=YES')
PY
    echo 'J129-PHONE-UX-V1-APPLY-PASS'
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
