#!/usr/bin/env bash
set -euo pipefail

PHONE_BASE="${PHONE_BASE:-http://192.168.1.167}"
REPORT_PATH="${REPORT_PATH:-/tmp/g10-19e4c-session-identity-source-trace.txt}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

log(){ printf '%s\n' "$1" | tee -a "$REPORT_PATH"; }
: > "$REPORT_PATH"

log 'scope=READ_ONLY_WEBAPP_SOURCE_TRACE'
log 'phone_write=NO'
log 'db_write=NO'
log 'pbx_live_code_write=NO'
log 'secrets_logged=NO'

curl -fsS --max-time 8 "$PHONE_BASE/" -o "$WORKDIR/root.html"
log 'root_fetch=SUCCESS'

python3 - "$WORKDIR/root.html" "$WORKDIR/assets.txt" <<'PY'
import re,sys
html=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
assets=set()
for pat in [r'<script[^>]+src=["\']([^"\']+)', r'<link[^>]+href=["\']([^"\']+\.js(?:\?[^"\']*)?)']:
    assets.update(re.findall(pat,html,re.I))
# Known filename observed in browser initiator; probe it even if dynamically loaded.
assets.update(['/webapp-0.js','webapp-0.js'])
for a in sorted(assets):
    print(a)
PY

count=0
hits_identity=0
hits_role=0
hits_post=0
while IFS= read -r asset; do
  [ -n "$asset" ] || continue
  case "$asset" in
    http://*|https://*) url="$asset" ;;
    /*) url="$PHONE_BASE$asset" ;;
    *) url="$PHONE_BASE/$asset" ;;
  esac
  out="$WORKDIR/asset-$count.js"
  if curl -fsS --max-time 8 "$url" -o "$out" 2>/dev/null; then
    size=$(wc -c < "$out" | tr -d ' ')
    idc=$(grep -ao 'session-identity' "$out" | wc -l | tr -d ' ' || true)
    rolec=$(grep -ao 'session-role' "$out" | wc -l | tr -d ' ' || true)
    postc=$(grep -ao 'api\.values\.post' "$out" | wc -l | tr -d ' ' || true)
    [ "$idc" -gt 0 ] && hits_identity=$((hits_identity+idc))
    [ "$rolec" -gt 0 ] && hits_role=$((hits_role+rolec))
    [ "$postc" -gt 0 ] && hits_post=$((hits_post+postc))
    safe_name=$(printf '%s' "$asset" | tr '\n\r=' '___')
    log "asset[$count].name=$safe_name"
    log "asset[$count].size=$size"
    log "asset[$count].session_identity_hits=$idc"
    log "asset[$count].session_role_hits=$rolec"
    log "asset[$count].api_values_post_hits=$postc"
    count=$((count+1))
  fi
done < "$WORKDIR/assets.txt"

log "assets_fetched=$count"
log "session_identity_total_hits=$hits_identity"
log "session_role_total_hits=$hits_role"
log "api_values_post_total_hits=$hits_post"

if [ "$hits_identity" -gt 0 ]; then
  log 'diagnostic=SESSION_IDENTITY_LITERAL_FOUND_IN_WEBAPP'
  log 'next_activity=G10-19E4D_TRACE_CREATION_CALLSITE'
else
  log 'diagnostic=SESSION_IDENTITY_LITERAL_NOT_FOUND_STATICALLY'
  log 'next_activity=G10-19E4D_CHROMIUM_CDP_RUNTIME_TRACE'
fi
log 'G10-19E4C-COMPLETE=YES'
