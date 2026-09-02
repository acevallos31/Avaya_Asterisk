#!/usr/bin/env python3
"""Prepara de forma controlada el Apply UX/Admin del workflow 11.

Solo modifica el checkout. El helper root sigue siendo la unica ruta autorizada
para cambios en LAB. Compatible con Python 3.6.
"""
from __future__ import print_function

from pathlib import Path
import sys

HELPER = Path("deploy/j129/avaya-j129-lab-deploy")
MARKER = "# J129-PHONE-UX-V3"


def main():
    text = HELPER.read_text()
    if MARKER in text:
        print("PHONE-UX-PREPARE-ALREADY-PRESENT")
        return 0

    case_marker = 'case "$ACTION" in\n'
    if case_marker not in text:
        print('ERROR: no se encontro case "$ACTION" in en helper', file=sys.stderr)
        return 1

    functions = r'''

# J129-PHONE-UX-V3
apply_phone_ux_v3() {
  local tpl=/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
  local backup=/var/lib/avaya-j129-lab/Avaya_global_SIP.tpl.pre-phone-ux-v3
  local defaults_file target_count target_id selected_other selected_after

  install -d -m 0755 /var/lib/avaya-j129-lab
  [ -f "$tpl" ] || { echo "ERROR: no existe $tpl" >&2; exit 1; }
  [ -f "$backup" ] || cp -a "$tpl" "$backup"

  defaults_file="$(make_db_defaults_file)"
  trap 'rm -f "$defaults_file"' RETURN EXIT

  target_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D';")"
  [ "$target_count" = "1" ] || { echo "ERROR: se esperaba exactamente un J129 objetivo y se encontraron $target_count" >&2; exit 1; }

  target_id="$(mysql_scalar "$defaults_file" "SELECT e.id FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' LIMIT 1;")"
  selected_other="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE selected=1 AND id<>${target_id};")"
  [ "$selected_other" = "0" ] || { echo "ERROR: hay otros endpoints seleccionados; se aborta" >&2; exit 1; }

  python3 - "$tpl" <<'PY'
from __future__ import print_function
import io
import sys

p = sys.argv[1]
with io.open(p, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

params = [
    ('PROCSTAT', '0'),
    ('PROVIDE_OPTIONS_SCREEN', '1'),
    ('PROVIDE_NETWORKINFO_SCREEN', '1'),
    ('PROVIDE_LOGOUT', '1'),
    ('ENTRYNAME', 'Briam'),
]

keys = set(k for k, _ in params)
kept = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('SET '):
        parts = stripped.split(None, 2)
        if len(parts) >= 2 and parts[1] in keys:
            continue
    kept.append(line)

kept.append('')
kept.append('## J129 LAB - UX/Admin controlado (workflow 11)')
for key, value in params:
    kept.append('SET %s %s' % (key, value))

with io.open(p, 'w', encoding='utf-8') as f:
    f.write('\n'.join(kept) + '\n')
PY

  mysql --defaults-extra-file="$defaults_file" endpointconfig -e "UPDATE endpoint SET selected=1 WHERE id=${target_id};"
  echo "PHONE_UX_SELECTED_ENDPOINT=${target_id}"

  if ! /usr/bin/issabel-endpointconfig --applyconfig; then
    echo 'ERROR: applyconfig fallo; restaurando template y selected' >&2
    cp -a "$backup" "$tpl"
    mysql --defaults-extra-file="$defaults_file" endpointconfig -e "UPDATE endpoint SET selected=0 WHERE id=${target_id};" || true
    exit 1
  fi

  selected_after="$(mysql_scalar "$defaults_file" "SELECT selected FROM endpoint WHERE id=${target_id};")"
  if [ "$selected_after" != "0" ]; then
    echo 'ERROR: Issabel no limpio selected del J129; corrigiendo selected y abortando' >&2
    mysql --defaults-extra-file="$defaults_file" endpointconfig -e "UPDATE endpoint SET selected=0 WHERE id=${target_id};" || true
    exit 1
  fi

  rm -f "$defaults_file"; trap - RETURN EXIT
  echo 'PHONE_UX_SELECTED_CLEARED=YES'
  echo 'J129-PHONE-UX-V3-APPLY-PASS'
}

phone_ux_sip_ok() {
  local defaults_file account out
  defaults_file="$(make_db_defaults_file)"
  trap 'rm -f "$defaults_file"' RETURN EXIT
  account="$(mysql_scalar "$defaults_file" "SELECT ea.account FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model JOIN endpoint_account ea ON ea.id_endpoint=e.id WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' ORDER BY ea.priority LIMIT 1;")"
  [ -n "$account" ] || { echo 'SIP_STATUS=NO_ACCOUNT'; exit 1; }
  out="$(asterisk -rx "sip show peer ${account}" 2>/dev/null || true)"
  if printf '%s\n' "$out" | grep -Eq 'Status[[:space:]]*: OK'; then
    echo "SIP_STATUS=OK account=${account}"
    rm -f "$defaults_file"; trap - RETURN EXIT
    return 0
  fi
  echo "SIP_STATUS=NOT_OK account=${account}"
  rm -f "$defaults_file"; trap - RETURN EXIT
  return 1
}

rollback_phone_ux_v3() {
  local tpl=/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
  local backup=/var/lib/avaya-j129-lab/Avaya_global_SIP.tpl.pre-phone-ux-v3
  [ -f "$backup" ] || { echo 'ERROR: no existe backup UX v3' >&2; exit 1; }
  cp -a "$backup" "$tpl"
  echo 'J129-PHONE-UX-V3-ROLLBACK-TEMPLATE-PASS'
}
'''

    text = text.replace(case_marker, functions + "\n" + case_marker, 1)
    dispatch = (
        case_marker
        + '  apply-phone-ux-v3) apply_phone_ux_v3 ;;\n'
        + '  phone-ux-sip-ok) phone_ux_sip_ok ;;\n'
        + '  rollback-phone-ux-v3) rollback_phone_ux_v3 ;;\n'
    )
    text = text.replace(case_marker, dispatch, 1)
    HELPER.write_text(text)
    print("PHONE-UX-PREPARE-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
