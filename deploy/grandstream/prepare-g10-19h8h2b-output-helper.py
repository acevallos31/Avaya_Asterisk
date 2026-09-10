#!/usr/bin/env python3
"""Extend the temporary integrated-applyconfig helper with one safe H8H2B output.

Run after prepare-integrated-applyconfig-helper.py. Only response/status tokens
from the H8H2B marker are emitted; arbitrary applyconfig output remains hidden.
"""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H8H2B-SAFE-OUTPUT'
if marker in s:
    print('G10-19H8H2B-OUTPUT-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

anchor = "  echo 'applyconfig_end_seen='$(grep -Fq 'END ENDPOINT CONFIGURATION' \"$raw\" && echo YES || echo NO)\n"
if s.count(anchor) != 1:
    raise SystemExit('H8H2B: integrated applyconfig output anchor not found exactly once')
block = anchor + r'''

  # G10-19H8H2B-SAFE-OUTPUT
  local h8h2b_class
  h8h2b_class="$(grep -Eo 'G10-19H8H2B-RESPONSE-CLASS response=[A-Za-z0-9_.-]{1,40} status=[A-Za-z0-9_.-]{1,40}' "$raw" | tail -n 1 || true)"
  if [ -n "$h8h2b_class" ]; then
    echo 'h8h2b_response_class_seen=YES'
    printf '%s\n' "$h8h2b_class"
  else
    echo 'h8h2b_response_class_seen=NO'
  fi
'''
s = s.replace(anchor, block, 1)
p.write_text(s, encoding='utf-8')
print('G10-19H8H2B-OUTPUT-HELPER-PREPARE=PASS')
