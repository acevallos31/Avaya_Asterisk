#!/usr/bin/env python3
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')

if 'run_grandstream_tftp_request_inspection()' not in s:
    marker = '\n[ -n "$ACTION" ] || usage\n'
    if marker not in s:
        raise SystemExit('helper insertion marker not found')
    fn = r'''

run_grandstream_tftp_request_inspection() {
  local phone_ip='192.168.1.167' cfg='cfgc074ade86609' tmp
  tmp="$(mktemp /tmp/grandstream-tftp-requests.XXXXXX)"
  chmod 0600 "$tmp"
  trap 'rm -f "$tmp"' RETURN EXIT
  echo '=== GRANDSTREAM TFTP REQUEST AUDIT (SOLO LECTURA) ==='
  echo "phone_ip=$phone_ip"
  echo "expected_cfg=$cfg"
  echo 'cfg_content_logged=NO'
  if journalctl -u xinetd --since '2 hours ago' --no-pager > "$tmp" 2>/dev/null; then
    echo 'source=xinetd-journal'
  elif [ -r /var/log/messages ]; then
    tail -n 12000 /var/log/messages > "$tmp"
    echo 'source=messages'
  else
    echo 'source=unavailable'
    echo 'GRANDSTREAM-TFTP-REQUEST-AUDIT-NO-SOURCE'
    return 0
  fi
  if grep -F "$phone_ip" "$tmp" >/dev/null 2>&1; then echo 'phone_ip_hit=YES'; else echo 'phone_ip_hit=NO'; fi
  if grep -Fi "$cfg" "$tmp" >/dev/null 2>&1; then echo 'expected_cfg_hit=YES'; else echo 'expected_cfg_hit=NO'; fi
  if grep -F "$phone_ip" "$tmp" 2>/dev/null | grep -Fi "$cfg" >/dev/null 2>&1; then
    echo 'phone_expected_cfg_correlated=YES'
  else
    echo 'phone_expected_cfg_correlated=NO'
  fi
  echo '=== TFTP RRQ FILENAMES (SANITIZED) ==='
  grep -Ei 'tftp|in\.tftpd' "$tmp" 2>/dev/null \
    | grep -F "$phone_ip" \
    | grep -Eo 'cfg[a-zA-Z0-9._-]+' \
    | sort -u \
    | head -n 20 || true
  rm -f "$tmp"; trap - RETURN EXIT
  echo 'GRANDSTREAM-TFTP-REQUEST-AUDIT-PASS'
}
'''
    s = s.replace(marker, fn + marker, 1)

old = "  inspect-sip-registration) [ -z \"$OVERLAY_ROOT\" ] || usage; run_sip_registration_inspection ;;\n"
new = old + "  inspect-grandstream-tftp-requests) [ -z \"$OVERLAY_ROOT\" ] || usage; run_grandstream_tftp_request_inspection ;;\n"
if 'inspect-grandstream-tftp-requests)' not in s:
    if old not in s:
        raise SystemExit('case insertion marker not found')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
