#!/usr/bin/env python3
from pathlib import Path
import os

cfg = Path('/tftpboot/cfgc074ade86609')
report = Path(os.environ.get('REPORT_PATH', '/tmp/g10-19g4.txt'))
lines = []

def log(k, v):
    lines.append(f'{k}={v}')

log('scope', 'READ_ONLY_CFG_MARKER_AUDIT')
log('db_write', 'NO')
log('phone_write', 'NO')
log('pbx_live_code_write', 'NO')
log('cfg_payload_dumped', 'NO')
log('sip_secret_logged', 'NO')

if not cfg.exists():
    log('cfg_state', 'ABSENT')
    log('diagnostic', 'CFG_MISSING')
else:
    data = cfg.read_bytes()
    log('cfg_state', 'PRESENT')
    log('cfg_size', str(len(data)))
    # Presence-only checks. Never print surrounding bytes or unknown values.
    checks = {
        'marker_ext_201_present': b'201' in data,
        'marker_ext_202_present': b'202' in data,
        'marker_fabi_present': b'Fabi' in data or b'FABI' in data or b'fabi' in data,
        'marker_ashly_present': b'Ashly' in data or b'ASHLY' in data or b'ashly' in data,
        'marker_pbx_ip_present': b'192.168.1.10' in data,
    }
    for k, v in checks.items():
        log(k, 'YES' if v else 'NO')

    if checks['marker_ext_202_present'] and not checks['marker_ext_201_present']:
        log('diagnostic', 'CFG_POINTS_TO_202_MARKER_PRESENT')
    elif checks['marker_ext_201_present'] and not checks['marker_ext_202_present']:
        log('diagnostic', 'CFG_STILL_POINTS_TO_201_MARKER_PRESENT')
    elif checks['marker_ext_201_present'] and checks['marker_ext_202_present']:
        log('diagnostic', 'CFG_CONTAINS_BOTH_201_AND_202_MARKERS')
    else:
        log('diagnostic', 'CFG_BINARY_MARKERS_INCONCLUSIVE')

log('G10-19G4-COMPLETE', 'YES')
report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
os.chmod(report, 0o600)
print('\n'.join(lines))
