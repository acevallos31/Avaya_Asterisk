#!/usr/bin/env python3
"""Prepara de forma controlada la fase de hora del workflow 10.

Solo modifica el checkout. El helper root sigue siendo la unica ruta autorizada
para cambios en LAB. Compatible con Python 3.6.
"""
from __future__ import print_function

from pathlib import Path
import sys

HELPER = Path("deploy/j129/avaya-j129-lab-deploy")


def main():
    text = HELPER.read_text()
    marker = "# J129-FORCED-TIME-V1"
    if marker in text:
        print("FORCED-TIME-PREPARE-ALREADY-PRESENT")
        return 0

    insert = r'''

# J129-FORCED-TIME-V1
apply_forced_time_v1() {
  local chrony=/etc/chrony.conf backup=/var/lib/avaya-j129-lab/chrony.conf.pre-forced-time
  local tpl=/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
  local tpl_backup=/var/lib/avaya-j129-lab/Avaya_global_SIP.tpl.pre-forced-time
  install -d -m 0755 /var/lib/avaya-j129-lab
  [ -f "$chrony" ] || { echo 'ERROR: falta /etc/chrony.conf' >&2; exit 1; }
  [ -f "$tpl" ] || { echo 'ERROR: falta template global Avaya' >&2; exit 1; }
  [ -f "$backup" ] || cp -a "$chrony" "$backup"
  [ -f "$tpl_backup" ] || cp -a "$tpl" "$tpl_backup"

  if ! grep -Eq '^[[:space:]]*allow[[:space:]]+192\.168\.1\.0/24([[:space:]]|$)' "$chrony"; then
    printf '\n# Avaya J129 LAB - NTP solo LAN\nallow 192.168.1.0/24\n' >> "$chrony"
  fi
  chronyd -p -f "$chrony" >/dev/null
  systemctl restart chronyd
  sleep 2
  ss -lun | grep -Eq '(^|[[:space:]:])123([[:space:]]|$)' || { echo 'ERROR: chronyd no escucha UDP/123' >&2; exit 1; }

  python3 - "$tpl" <<'PY'
from __future__ import print_function
import io, sys
p = sys.argv[1]
with io.open(p, 'r', encoding='utf-8') as f:
    s = f.read()
block = ("\n## Hora J129 LAB - parametros oficiales Avaya\n"
         "SET SNTPSRVR 192.168.1.10\n"
         "SET SNTP_SYNC_INTERVAL 60\n"
         "SET GMTOFFSET -6:00\n"
         "SET DAYLIGHT_SAVING_SETTING_MODE 0\n")
if 'SET SNTPSRVR 192.168.1.10' not in s:
    anchor = '## Cada teléfono obtiene sus credenciales desde su archivo específico por MAC.\n'
    if anchor not in s:
        raise SystemExit('ERROR: anchor template no encontrado')
    s = s.replace(anchor, block + '\n' + anchor, 1)
with io.open(p, 'w', encoding='utf-8') as f:
    f.write(s)
PY
  /usr/bin/issabel-endpointconfig --applyconfig
  echo 'J129-FORCED-TIME-APPLY-PASS'
}

rollback_forced_time_v1() {
  local backup=/var/lib/avaya-j129-lab/chrony.conf.pre-forced-time
  local tpl_backup=/var/lib/avaya-j129-lab/Avaya_global_SIP.tpl.pre-forced-time
  [ -f "$backup" ] && cp -a "$backup" /etc/chrony.conf
  [ -f "$tpl_backup" ] && cp -a "$tpl_backup" /usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
  systemctl restart chronyd
  /usr/bin/issabel-endpointconfig --applyconfig || true
  echo 'J129-FORCED-TIME-ROLLBACK-PASS'
}
'''
    case = 'case "$ACTION" in\n'
    if case not in text:
        print("ERROR: no se encontro case ACTION", file=sys.stderr)
        return 1
    text = text.replace(case, insert + "\n" + case, 1)
    needle = 'case "$ACTION" in\n'
    repl = needle + '  apply-forced-time-v1) apply_forced_time_v1 ;;\n  rollback-forced-time-v1) rollback_forced_time_v1 ;;\n'
    text = text.replace(needle, repl, 1)
    HELPER.write_text(text)
    print("FORCED-TIME-PREPARE-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
