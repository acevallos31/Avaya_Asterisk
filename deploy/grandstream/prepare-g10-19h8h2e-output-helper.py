#!/usr/bin/env python3
"""Expose only the fixed H8H2E login classification from hidden applyconfig logs."""
from pathlib import Path
p=Path('deploy/j129/avaya-j129-lab-deploy')
s=p.read_text(encoding='utf-8')
marker='# G10-19H8H2E-SAFE-OUTPUT'
if marker in s:
    print('G10-19H8H2E-OUTPUT-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)
anchor="  echo 'applyconfig_end_seen='$(grep -Fq 'END ENDPOINT CONFIGURATION' \"$raw\" && echo YES || echo NO)\n"
if s.count(anchor)!=1: raise SystemExit('H8H2E output anchor mismatch')
block=anchor+r'''

  # G10-19H8H2E-SAFE-OUTPUT
  local h8h2e_class
  h8h2e_class="$(grep -Eo 'G10-19H8H2E-LOGIN-CLASS response_success=(YES|NO) body_dict=(YES|NO) sid_present=(YES|NO)' "$raw" | tail -n 1 || true)"
  if [ -n "$h8h2e_class" ]; then
    echo 'h8h2e_login_class_seen=YES'
    printf '%s\n' "$h8h2e_class"
  else
    echo 'h8h2e_login_class_seen=NO'
  fi
'''
s=s.replace(anchor,block,1)
p.write_text(s,encoding='utf-8')
print('G10-19H8H2E-OUTPUT-HELPER-PREPARE=PASS')
