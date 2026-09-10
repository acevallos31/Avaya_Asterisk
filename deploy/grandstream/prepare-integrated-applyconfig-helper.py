#!/usr/bin/env python3
from pathlib import Path

p=Path('deploy/j129/avaya-j129-lab-deploy')
s=p.read_text(encoding='utf-8')
marker='# G10-19H8F-INTEGRATED-APPLYCONFIG'
if marker in s:
    print('G10-19H8F-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)
anchor='\n[ -n "$ACTION" ] || usage\n'
if anchor not in s:
    raise SystemExit('ERROR: helper action anchor missing')

func=r'''

# G10-19H8F-INTEGRATED-APPLYCONFIG
run_grandstream_integrated_applyconfig() {
  local defaults_file selected_count target_count active_count raw backup_dir
  local bin='/tftpboot/cfgc074ade86609' xml='/tftpboot/cfgc074ade86609.xml'
  local baseline_epoch rc xml_mtime xml_size bin_mtime bin_size

  [ -x /usr/bin/issabel-endpointconfig ] || { echo 'ERROR: issabel-endpointconfig unavailable' >&2; exit 1; }
  [ -f "$GRANDSTREAM_PY" ] || { echo 'ERROR: live Grandstream.py unavailable' >&2; exit 1; }
  grep -Fq '# G10-19H6-INTEGRATED-XML-GENERATOR' "$GRANDSTREAM_PY" || { echo 'ERROR: integrated XML generator marker absent' >&2; exit 1; }
  [ "$(grep -Fc '# G10-19H8F0-SAFE-ERROR-LOGGING' "$GRANDSTREAM_PY" || true)" -ge 2 ] || { echo 'ERROR: safe logging hardening absent' >&2; exit 1; }
  python3 -m py_compile "$GRANDSTREAM_PY"

  defaults_file="$(make_db_defaults_file)"; trap 'rm -f "$defaults_file"' RETURN EXIT
  selected_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint WHERE selected=1;")"
  target_count="$(mysql_scalar "$defaults_file" "SELECT COUNT(*) FROM endpoint e JOIN manufacturer mf ON mf.id=e.id_manufacturer LEFT JOIN model m ON m.id=e.id_model JOIN endpoint_account ea ON ea.id_endpoint=e.id WHERE e.selected=1 AND mf.name='Grandstream' AND m.name='GXP1625' AND e.mac_address='C0:74:AD:E8:66:09' AND e.last_known_ipv4='192.168.1.167' AND ea.account='202';")"
  [ "$selected_count" -eq 1 ] || { echo "ERROR: selected endpoint count changed: $selected_count" >&2; exit 1; }
  [ "$target_count" -eq 1 ] || { echo "ERROR: selected endpoint is not exact GXP1625/202 target: $target_count" >&2; exit 1; }

  if pgrep -af '[i]ssabel-endpointconfig.*applyconfig' >/dev/null 2>&1; then
    echo 'ERROR: another applyconfig is already running' >&2; exit 1
  fi

  active_count="$(asterisk -rx 'core show channels concise' 2>/dev/null | awk -F'!' '$1 ~ /^SIP\/202-/ {n++} END{print n+0}')"
  [ "$active_count" -eq 0 ] || { echo "ERROR: active SIP/202 channel exists; refusing provisioning: $active_count" >&2; exit 1; }

  install -d -m 0700 "$STATE_DIR"
  backup_dir="$(mktemp -d "$STATE_DIR/g10-19h8f.XXXXXX")"
  chmod 0700 "$backup_dir"
  [ -f "$bin" ] && cp -a "$bin" "$backup_dir/cfg.bin.pre" || true
  [ -f "$xml" ] && cp -a "$xml" "$backup_dir/cfg.xml.pre" || true
  [ -f "$backup_dir/cfg.bin.pre" ] && chmod 0600 "$backup_dir/cfg.bin.pre"
  [ -f "$backup_dir/cfg.xml.pre" ] && chmod 0600 "$backup_dir/cfg.xml.pre"

  # Remove only XML so its reappearance proves generation by the live integrated class.
  rm -f "$xml"
  [ ! -e "$xml" ] || { echo 'ERROR: XML could not be removed for regeneration proof' >&2; exit 1; }
  baseline_epoch="$(date +%s)"
  sleep 2
  raw="$(mktemp /tmp/g10-19h8f-applyconfig.XXXXXX.log)"
  chmod 0600 "$raw"

  set +e
  /usr/bin/issabel-endpointconfig --applyconfig >"$raw" 2>&1
  rc=$?
  set -e

  echo 'scope=CONTROLLED_SINGLE_ENDPOINT_INTEGRATED_APPLYCONFIG'
  echo 'db_write=NO_DIRECT_DB_WRITE'
  echo 'phone_direct_sip_write=NO'
  echo 'factory_reset=NO'
  echo 'raw_applyconfig_log_exposed=NO'
  echo 'sip_secret_logged_by_safe_patch=NO'
  echo "selected_count=$selected_count"
  echo "target_selected_count=$target_count"
  echo "active_sip_202_channels_before=$active_count"
  echo 'xml_removed_before_apply=YES'
  echo "applyconfig_rc=$rc"

  # Publish only known-safe lifecycle messages, never arbitrary exception/payload text.
  echo 'applyconfig_begin_seen='$(grep -Fq 'BEGIN ENDPOINT CONFIGURATION' "$raw" && echo YES || echo NO)
  echo 'grandstream_start_seen='$(grep -Eq 'starting configuration for endpoint Grandstream@192\.168\.1\.167' "$raw" && echo YES || echo NO)
  echo 'grandstream_finished_seen='$(grep -Eq 'finished configuration for endpoint Grandstream@192\.168\.1\.167' "$raw" && echo YES || echo NO)
  echo 'grandstream_failed_seen='$(grep -Eq 'failed configuration for endpoint Grandstream@192\.168\.1\.167' "$raw" && echo YES || echo NO)
  echo 'applyconfig_end_seen='$(grep -Fq 'END ENDPOINT CONFIGURATION' "$raw" && echo YES || echo NO)

  if [ ! -f "$xml" ]; then
    echo 'xml_recreated=NO'
    # Restore the known-good XML if integrated generation failed.
    if [ -f "$backup_dir/cfg.xml.pre" ]; then
      cp -a "$backup_dir/cfg.xml.pre" "$xml"
      echo 'xml_failure_restore=YES'
    else
      echo 'xml_failure_restore=NO_PREVIOUS_XML'
    fi
    rm -f "$raw"
    rm -rf "$backup_dir"
    rm -f "$defaults_file"; trap - RETURN EXIT
    echo 'G10-19H8F-INTEGRATED-APPLYCONFIG-FAIL'
    return 1
  fi

  xml_mtime="$(stat -c %Y "$xml")"; xml_size="$(stat -c %s "$xml")"
  bin_mtime="$(stat -c %Y "$bin")"; bin_size="$(stat -c %s "$bin")"
  echo 'xml_recreated=YES'
  echo "xml_mtime_after_baseline=$([ "$xml_mtime" -ge "$baseline_epoch" ] && echo YES || echo NO)"
  echo "xml_size=$xml_size"
  echo "binary_present=$([ -f "$bin" ] && echo YES || echo NO)"
  echo "binary_size=$bin_size"

  python3 - "$xml" <<'PY'
import sys, xml.etree.ElementTree as ET
p=sys.argv[1]
root=ET.parse(p).getroot()
vals={c.tag:(c.text or '') for c in root.find('config')}
print('xml_root_valid=' + ('YES' if root.tag=='gs_provision' else 'NO'))
print('xml_mac_binding=' + ('YES' if (root.findtext('mac') or '').lower()=='c074ade86609' else 'NO'))
print('xml_p35_target_202=' + ('YES' if vals.get('P35')=='202' else 'NO'))
print('xml_p36_target_202=' + ('YES' if vals.get('P36')=='202' else 'NO'))
print('xml_p34_secret_present=' + ('YES' if bool(vals.get('P34')) else 'NO'))
print('xml_p47_target_pbx=' + ('YES' if vals.get('P47')=='192.168.1.10' else 'NO'))
print('xml_p270_target_ashly=' + ('YES' if 'ashly' in vals.get('P270','').lower() else 'NO'))
PY

  # Validate without ever printing XML or secret values.
  python3 - "$xml" <<'PY'
import sys, xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot(); cfg=root.find('config')
if root.tag!='gs_provision' or cfg is None: raise SystemExit(1)
v={c.tag:(c.text or '') for c in cfg}
assert (root.findtext('mac') or '').lower()=='c074ade86609'
assert v.get('P35')=='202' and v.get('P36')=='202'
assert bool(v.get('P34'))
assert v.get('P47')=='192.168.1.10'
assert 'ashly' in v.get('P270','').lower()
PY

  # Backup served only as rollback during this test; remove secret-bearing copies on success.
  rm -f "$raw"
  rm -rf "$backup_dir"
  rm -f "$defaults_file"; trap - RETURN EXIT
  echo 'rollback_backup_retained=NO_SUCCESS_CLEANUP'
  echo 'diagnostic=INTEGRATED_ENDPOINTCONFIG_XML_REGENERATION_PASS'
  echo 'G10-19H8F-INTEGRATED-APPLYCONFIG-PASS'
}
'''
s=s.replace(anchor,func+anchor,1)
case_anchor='  inspect-login-patch) [ -z "$OVERLAY_ROOT" ] || usage; inspect_grandstream_login_patch ;;'
if case_anchor not in s:
    raise SystemExit('ERROR: helper case anchor missing')
s=s.replace(case_anchor,case_anchor+'\n  run-grandstream-integrated-applyconfig) [ -z "$OVERLAY_ROOT" ] || usage; run_grandstream_integrated_applyconfig ;;',1)
p.write_text(s,encoding='utf-8')
print('G10-19H8F-HELPER-PREPARE=PASS')
