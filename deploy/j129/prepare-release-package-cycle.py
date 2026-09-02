#!/usr/bin/env python3
from __future__ import print_function
from pathlib import Path
import sys

HELPER = Path('deploy/j129/avaya-j129-lab-deploy')
MARKER = '# J129-RELEASE-PACKAGE-CYCLE-V010'

text = HELPER.read_text()
if MARKER in text:
    print('RELEASE-PACKAGE-PREPARE-ALREADY-PRESENT')
    sys.exit(0)

case_marker = 'case "$ACTION" in\n'
if case_marker not in text:
    raise SystemExit('No se encontro case principal del helper')

func = r'''

# J129-RELEASE-PACKAGE-CYCLE-V010
release_package_cycle_v010() {
  local checkout_root="$1"
  local release_root="$checkout_root/release/j129-v0.1.0"
  local installer="$release_root/install.sh"
  local df before_vendor before_j129 before_global before_http before_max before_sip before_iax
  local after_vendor after_j129 after_global after_http after_max after_sip after_iax

  [ -f "$installer" ] || { echo "ERROR: falta $installer" >&2; exit 1; }
  [ -d "$release_root/payload" ] || { echo "ERROR: falta payload de release" >&2; exit 1; }
  bash -n "$installer"

  hash_or_absent() { if [ -f "$1" ]; then sha256sum "$1" | awk '{print $1}'; else echo ABSENT; fi; }
  before_vendor="$(hash_or_absent /usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py)"
  before_j129="$(hash_or_absent /usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl)"
  before_global="$(hash_or_absent /usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl)"
  before_http="$(hash_or_absent /etc/httpd/conf.d/avaya-j129-provisioning.conf)"

  df="$(make_db_defaults_file)"; trap 'rm -f "$df"' RETURN EXIT
  before_max="$(mysql_scalar "$df" "SELECT COALESCE(MAX(m.max_accounts),0) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")"
  before_sip="$(mysql_scalar "$df" "SELECT COALESCE(MAX(mp.property_value),0) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts';")"
  before_iax="$(mysql_scalar "$df" "SELECT COALESCE(MAX(mp.property_value),0) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts';")"
  rm -f "$df"; trap - RETURN EXIT

  echo "RELEASE_BASELINE_FILES vendor=$before_vendor j129=$before_j129 global=$before_global http=$before_http"
  echo "RELEASE_BASELINE_DB max=$before_max sip=$before_sip iax=$before_iax"

  bash "$installer" preflight
  bash "$installer" install
  bash "$installer" verify
  echo 'RELEASE-FIRST-INSTALL-PASS'

  bash "$installer" install
  bash "$installer" verify
  echo 'RELEASE-SECOND-INSTALL-IDEMPOTENT-PASS'

  bash "$installer" rollback

  after_vendor="$(hash_or_absent /usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py)"
  after_j129="$(hash_or_absent /usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl)"
  after_global="$(hash_or_absent /usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl)"
  after_http="$(hash_or_absent /etc/httpd/conf.d/avaya-j129-provisioning.conf)"

  df="$(make_db_defaults_file)"; trap 'rm -f "$df"' RETURN EXIT
  after_max="$(mysql_scalar "$df" "SELECT COALESCE(MAX(m.max_accounts),0) FROM model m JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129';")"
  after_sip="$(mysql_scalar "$df" "SELECT COALESCE(MAX(mp.property_value),0) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_sip_accounts';")"
  after_iax="$(mysql_scalar "$df" "SELECT COALESCE(MAX(mp.property_value),0) FROM model_properties mp JOIN model m ON m.id=mp.id_model JOIN manufacturer mf ON mf.id=m.id_manufacturer WHERE mf.name='Avaya' AND m.name='J129' AND mp.property_key='max_iax2_accounts';")"
  rm -f "$df"; trap - RETURN EXIT

  [ "$after_vendor" = "$before_vendor" ] || { echo 'ERROR: release rollback no restauro Avaya.py' >&2; exit 1; }
  [ "$after_j129" = "$before_j129" ] || { echo 'ERROR: release rollback no restauro Avaya_J129.tpl' >&2; exit 1; }
  [ "$after_global" = "$before_global" ] || { echo 'ERROR: release rollback no restauro Avaya_global_SIP.tpl' >&2; exit 1; }
  [ "$after_http" = "$before_http" ] || { echo 'ERROR: release rollback no restauro Apache conf' >&2; exit 1; }
  [ "$after_max" = "$before_max" ] || { echo 'ERROR: release rollback no restauro max_accounts' >&2; exit 1; }
  [ "$after_sip" = "$before_sip" ] || { echo 'ERROR: release rollback no restauro max_sip_accounts' >&2; exit 1; }
  [ "$after_iax" = "$before_iax" ] || { echo 'ERROR: release rollback no restauro max_iax2_accounts' >&2; exit 1; }

  echo 'RELEASE-ROLLBACK-EXACT-PASS'
  echo 'J129-RELEASE-PACKAGE-V010-LAB-PASS'
}
'''

text = text.replace(case_marker, func + '\n' + case_marker, 1)
dispatch = case_marker + '  release-package-cycle-v010) [ -n "$OVERLAY_ROOT" ] || usage; release_package_cycle_v010 "$OVERLAY_ROOT" ;;\n'
text = text.replace(case_marker, dispatch, 1)
HELPER.write_text(text)
print('RELEASE-PACKAGE-PREPARE-PASS')
