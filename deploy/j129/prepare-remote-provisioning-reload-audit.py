from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text()

marker = 'install_http_j129() {'
if marker not in s:
    raise SystemExit('ERROR: no se encontro marker para insertar remote provisioning reload')

if 'run_remote_provisioning_reload() {' not in s:
    fn = r'''run_remote_provisioning_reload() {
  local defaults_file account phone_ip peer_out channels_out notify_out baseline_epoch deadline now
  local compact log fresh_file tmp http_ok=0 sip_ok=0 saw_down=0

  command -v asterisk >/dev/null 2>&1 || { echo 'ERROR: asterisk CLI no disponible' >&2; exit 1; }
  defaults_file="$(make_db_defaults_file)"
  tmp="$(mktemp /tmp/j129-remote-reload.XXXXXX)"
  chmod 0600 "$tmp"
  trap 'rm -f "$defaults_file" "$tmp"' RETURN EXIT

  account="$(mysql_scalar "$defaults_file" "SELECT ea.account FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model JOIN endpoint_account ea ON ea.id_endpoint=e.id WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' ORDER BY ea.priority LIMIT 1;")"
  phone_ip="$(mysql_scalar "$defaults_file" "SELECT e.last_known_ipv4 FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer JOIN model m ON m.id=e.id_model WHERE mf.name='Avaya' AND m.name='J129' AND e.mac_address='C8:1F:EA:9B:65:0D' LIMIT 1;")"

  [ -n "$account" ] || { echo 'ERROR: J129 sin cuenta asignada' >&2; exit 1; }
  [ -n "$phone_ip" ] || { echo 'ERROR: J129 sin IP conocida' >&2; exit 1; }
  compact='c81fea9b650d'

  echo '=== J129 REMOTE RESTART + PROVISIONING AUDIT ==='
  echo "Cuenta=$account"
  echo "IP=$phone_ip"
  echo 'Secretos SIP: no consultados'

  peer_out="$(asterisk -rx "sip show peer ${account}" 2>/dev/null || true)"
  printf '%s\n' "$peer_out" | grep -Ei '(^|[[:space:]])Addr->IP|Useragent|Status' || true
  printf '%s\n' "$peer_out" | grep -Eiq 'Avaya|J129|J100' || { echo "ERROR: peer $account no se identifica como Avaya/J129" >&2; exit 1; }
  printf '%s\n' "$peer_out" | grep -F "$phone_ip" >/dev/null 2>&1 || { echo "ERROR: peer $account no esta registrado desde $phone_ip" >&2; exit 1; }

  channels_out="$(asterisk -rx 'core show channels concise' 2>/dev/null || true)"
  if printf '%s\n' "$channels_out" | grep -E "(^|/)${account}-" >/dev/null 2>&1; then
    echo "ERROR: existen canales activos del peer $account; prueba cancelada" >&2
    exit 1
  fi

  grep -A4 -E '^\[aastra-check-cfg\]' /etc/asterisk/sip_notify.conf | grep -Eiq '^[[:space:]]*Event[[:space:]]*=>[[:space:]]*check-sync[[:space:]]*$' || { echo 'ERROR: aastra-check-cfg no contiene Event=>check-sync' >&2; exit 1; }

  baseline_epoch="$(date +%s)"
  echo "BASELINE_EPOCH=$baseline_epoch"
  echo "NOTIFY_DESTINO=$account"
  notify_out="$(asterisk -rx "sip notify aastra-check-cfg ${account}" 2>&1)"
  printf '%s\n' "$notify_out"
  echo 'NOTIFY_ENVIADO=1'
  echo 'VENTANA_OBSERVACION=300s'

  # El J129 puede tardar varios minutos en reiniciar. Observamos hasta 5 minutos.
  # No dependemos solo de ping/HTTPS: la prueba fuerte es nueva descarga HTTP y
  # posterior registro SIP desde la IP esperada.
  deadline=$((baseline_epoch + 300))
  fresh_file=''
  while :; do
    now="$(date +%s)"

    peer_out="$(asterisk -rx "sip show peer ${account}" 2>/dev/null || true)"
    if ! printf '%s\n' "$peer_out" | grep -F "$phone_ip" >/dev/null 2>&1 || ! printf '%s\n' "$peer_out" | grep -Eq 'Status[[:space:]]*:[[:space:]]*OK'; then
      if [ "$saw_down" -eq 0 ]; then
        echo "RESTART_EVIDENCE=peer-down-or-not-ok t=$((now-baseline_epoch))s"
      fi
      saw_down=1
    fi

    : > "$tmp"
    for log in /var/log/httpd/access_log /var/log/httpd/*access*.log; do
      [ -f "$log" ] || continue
      if [ "$(stat -c %Y "$log")" -ge "$baseline_epoch" ]; then
        grep -F "$phone_ip" "$log" 2>/dev/null | tail -n 300 >> "$tmp" || true
      fi
    done

    if grep -Fi '46xxsettings.txt' "$tmp" >/dev/null 2>&1 && grep -Fi "${compact}.txt" "$tmp" >/dev/null 2>&1; then
      http_ok=1
      for log in /var/log/httpd/access_log /var/log/httpd/*access*.log; do
        [ -f "$log" ] || continue
        if [ "$(stat -c %Y "$log")" -ge "$baseline_epoch" ] && grep -F "$phone_ip" "$log" | tail -n 120 | grep -E "46xxsettings\.txt|${compact}\.txt|J100Supgrade\.txt" >/dev/null 2>&1; then
          fresh_file="$log"
          break
        fi
      done
    fi

    peer_out="$(asterisk -rx "sip show peer ${account}" 2>/dev/null || true)"
    if printf '%s\n' "$peer_out" | grep -F "$phone_ip" >/dev/null 2>&1 && printf '%s\n' "$peer_out" | grep -Eq 'Status[[:space:]]*:[[:space:]]*OK'; then
      sip_ok=1
    else
      sip_ok=0
    fi

    if [ "$http_ok" -eq 1 ] && [ "$sip_ok" -eq 1 ]; then
      break
    fi
    [ "$now" -ge "$deadline" ] && break
    sleep 5
  done

  echo '=== EVIDENCIA HTTP POST-NOTIFY ==='
  if [ "$http_ok" -eq 1 ] && [ -n "$fresh_file" ]; then
    grep -F "$phone_ip" "$fresh_file" | tail -n 120 | grep -E "46xxsettings\.txt|${compact}\.txt|J100Supgrade\.txt" | tail -n 20 || true
    echo 'HTTP_PROVISIONING_POST_NOTIFY=PASS'
  else
    echo 'HTTP_PROVISIONING_POST_NOTIFY=FAIL'
  fi

  echo '=== SIP POST-RESTART ==='
  peer_out="$(asterisk -rx "sip show peer ${account}" 2>/dev/null || true)"
  printf '%s\n' "$peer_out" | grep -Ei '(^|[[:space:]])Addr->IP|Useragent|Status' || true
  if [ "$sip_ok" -eq 1 ]; then
    echo 'SIP_REREGISTRATION=PASS'
  else
    echo 'SIP_REREGISTRATION=FAIL'
  fi

  echo "RESTART_DOWN_OBSERVED=$saw_down"
  if [ "$http_ok" -ne 1 ] || [ "$sip_ok" -ne 1 ]; then
    echo 'J129-REMOTE-RESTART-PROVISIONING-FAIL'
    exit 1
  fi

  rm -f "$defaults_file" "$tmp"
  trap - RETURN EXIT
  echo 'J129-REMOTE-RESTART-PROVISIONING-PASS'
}

'''
    s = s.replace(marker, fn + marker, 1)

needle = '  inspect-sip-registration) [ -z "$OVERLAY_ROOT" ] || usage; run_sip_registration_inspection ;;'
if needle not in s:
    raise SystemExit('ERROR: no se encontro case inspect-sip-registration')

if 'remote-provisioning-reload)' not in s:
    s = s.replace(needle, needle + '\n  remote-provisioning-reload) [ -z "$OVERLAY_ROOT" ] || usage; run_remote_provisioning_reload ;;', 1)

p.write_text(s)
print('REMOTE-PROVISIONING-RELOAD-PREPARE-PASS')
