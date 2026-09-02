from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text()

marker = 'install_http_j129() {'
if marker not in s:
    raise SystemExit('ERROR: no se encontro marker para insertar remote provisioning reload')

if 'run_remote_provisioning_reload() {' not in s:
    fn = r'''run_remote_provisioning_reload() {
  local defaults_file account phone_ip peer_out channels_out notify_out baseline_epoch deadline now
  local compact log found=0 fresh_file tmp

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

  echo '=== J129 REMOTE PROVISIONING RELOAD AUDIT ==='
  echo "Cuenta=$account"
  echo "IP=$phone_ip"
  echo 'Secretos SIP: no consultados'

  peer_out="$(asterisk -rx "sip show peer ${account}" 2>/dev/null || true)"
  printf '%s\n' "$peer_out" | grep -Ei '(^|[[:space:]])Addr->IP|Useragent|Status' || true
  printf '%s\n' "$peer_out" | grep -Eiq 'Avaya|J129|J100' || {
    echo "ERROR: peer $account no se identifica como Avaya/J129" >&2
    exit 1
  }
  printf '%s\n' "$peer_out" | grep -F "$phone_ip" >/dev/null 2>&1 || {
    echo "ERROR: peer $account no esta registrado desde $phone_ip" >&2
    exit 1
  }

  channels_out="$(asterisk -rx 'core show channels concise' 2>/dev/null || true)"
  if printf '%s\n' "$channels_out" | grep -E "(^|/)${account}-" >/dev/null 2>&1; then
    echo "ERROR: existen canales activos del peer $account; prueba cancelada" >&2
    exit 1
  fi

  grep -A4 -E '^\[aastra-check-cfg\]' /etc/asterisk/sip_notify.conf | grep -Eiq '^[[:space:]]*Event[[:space:]]*=>[[:space:]]*check-sync[[:space:]]*$' || {
    echo 'ERROR: aastra-check-cfg no contiene Event=>check-sync' >&2
    exit 1
  }

  baseline_epoch="$(date +%s)"
  echo "BASELINE_EPOCH=$baseline_epoch"
  echo "NOTIFY_DESTINO=$account"
  notify_out="$(asterisk -rx "sip notify aastra-check-cfg ${account}" 2>&1)"
  printf '%s\n' "$notify_out"
  echo 'NOTIFY_ENVIADO=1'

  deadline=$((baseline_epoch + 100))
  fresh_file=''
  while :; do
    now="$(date +%s)"
    : > "$tmp"
    for log in /var/log/httpd/access_log /var/log/httpd/*access*.log; do
      [ -f "$log" ] || continue
      grep -F "$phone_ip" "$log" 2>/dev/null | tail -n 250 >> "$tmp" || true
    done

    if grep -Fi '46xxsettings.txt' "$tmp" >/dev/null 2>&1 && grep -Fi "${compact}.txt" "$tmp" >/dev/null 2>&1; then
      for log in /var/log/httpd/access_log /var/log/httpd/*access*.log; do
        [ -f "$log" ] || continue
        if [ "$(stat -c %Y "$log")" -ge "$baseline_epoch" ] && \
           grep -F "$phone_ip" "$log" | tail -n 80 | grep -E "46xxsettings\.txt|${compact}\.txt|J100Supgrade\.txt" >/dev/null 2>&1; then
          fresh_file="$log"
          found=1
          break
        fi
      done
    fi

    [ "$found" -eq 1 ] && break
    [ "$now" -ge "$deadline" ] && break
    sleep 5
  done

  echo '=== EVIDENCIA HTTP POST-NOTIFY ==='
  if [ "$found" -eq 1 ]; then
    grep -F "$phone_ip" "$fresh_file" | tail -n 80 | grep -E "46xxsettings\.txt|${compact}\.txt|J100Supgrade\.txt" | tail -n 20 || true
  else
    echo 'SIN-NUEVA-DESCARGA-DE-PROVISIONING'
    echo 'J129-REMOTE-PROVISIONING-RELOAD-FAIL'
    exit 1
  fi

  echo '=== SIP POST-RELOAD ==='
  asterisk -rx 'sip show peers' 2>/dev/null | grep -E "(^|[[:space:]])${account}(/|[[:space:]])" | grep -F "$phone_ip" | sed -E 's/[[:space:]]+/ /g' || true

  rm -f "$defaults_file" "$tmp"
  trap - RETURN EXIT
  echo 'J129-REMOTE-PROVISIONING-RELOAD-PASS'
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
