#!/usr/bin/env python3
"""Extend the integrated applyconfig helper with H8H2C safe stage output."""
from pathlib import Path

p = Path('deploy/j129/avaya-j129-lab-deploy')
s = p.read_text(encoding='utf-8')
marker = '# G10-19H8H2C-SAFE-OUTPUT'
if marker in s:
    print('G10-19H8H2C-OUTPUT-HELPER-PREPARE=ALREADY_PRESENT')
    raise SystemExit(0)

anchor = "  echo 'applyconfig_end_seen='$(grep -Fq 'END ENDPOINT CONFIGURATION' \"$raw\" && echo YES || echo NO)\n"
if s.count(anchor) != 1:
    raise SystemExit('H8H2C integrated output anchor not found exactly once')
block = anchor + r'''

  # G10-19H8H2C-SAFE-OUTPUT
  local h8h2c_stages
  h8h2c_stages="$(grep -Eo 'G10-19H8H2C-STAGE=[A-Z_]+' "$raw" | awk '!seen[$0]++' || true)"
  if [ -n "$h8h2c_stages" ]; then
    echo 'h8h2c_stage_trace_seen=YES'
    printf '%s\n' "$h8h2c_stages"
  else
    echo 'h8h2c_stage_trace_seen=NO'
  fi
'''
s = s.replace(anchor, block, 1)
p.write_text(s, encoding='utf-8')
print('G10-19H8H2C-OUTPUT-HELPER-PREPARE=PASS')
