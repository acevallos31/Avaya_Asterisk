from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text()

marker = 'install_http_j129() {'
if marker not in s:
    raise SystemExit('ERROR: no se encontro marker para insertar send_j129_check_sync')

if 'send_j129_check_sync() {' not in s:
    fn = r'''send_j129_check_sync() {
  local peer='201' peer_out channels_out notify_out
  command -v asterisk >/dev/null 2>&1 || { echo 'ERROR: asterisk CLI no disponible' >&2; exit 1; }
  echo '=== PRECHECK J129 ==='
  peer_out="$(asterisk -rx "sip show peer ${peer}" 2>/dev/null || true)"
  [ -n "$peer_out" ] || {
    echo 'ERROR: peer 201 no existe o no puede consultarse' >&2
    exit 1
  }
  printf '%s\n' "$peer_out" | grep -Ei '(^|[[:space:]])Addr->IP|Useragent|Status' || true
  printf '%s\n' "$peer_out" | grep -Eiq 'Avaya|J129|J100' || {
    echo 'ERROR: peer 201 no se identifica como telefono Avaya/J129' >&2
    exit 1
  }
  channels_out="$(asterisk -rx 'core show channels concise' 2>/dev/null || true)"
  if printf '%s\n' "$channels_out" | grep -E "(^|/)${peer}-" >/dev/null 2>&1; then
    echo 'ERROR: existen canales activos del peer 201; NOTIFY cancelado' >&2
    exit 1
  fi
  grep -A4 -E '^\[aastra-check-cfg\]' /etc/asterisk/sip_notify.conf | grep -Eiq '^[[:space:]]*Event[[:space:]]*=>[[:space:]]*check-sync[[:space:]]*$' || {
    echo 'ERROR: tipo aastra-check-cfg no contiene Event=>check-sync' >&2
    exit 1
  }
  echo 'PRECHECK-NOTIFY=PASS'
  echo 'NOTIFY-TIPO=check-sync'
  echo 'NOTIFY-DESTINO=peer-201-j129-lab'
  notify_out="$(asterisk -rx 'sip notify aastra-check-cfg 201' 2>&1)"
  printf '%s\n' "$notify_out"
  echo 'NOTIFY-ENVIADO=1'
  echo 'NOTIFY-CANTIDAD=1'
}

'''
    s = s.replace(marker, fn + marker, 1)

needle = '  inspect-sip-registration) [ -z "$OVERLAY_ROOT" ] || usage; run_sip_registration_inspection ;;'
if needle not in s:
    raise SystemExit('ERROR: no se encontro case inspect-sip-registration')

if 'send-j129-check-sync)' not in s:
    s = s.replace(needle, needle + '\n  send-j129-check-sync) [ -z "$OVERLAY_ROOT" ] || usage; send_j129_check_sync ;;', 1)

p.write_text(s)
print('HELPER-CONTROLLED-CHECK-SYNC-PATCH=PASS')
