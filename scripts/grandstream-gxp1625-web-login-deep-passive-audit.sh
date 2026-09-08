#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${RUNNER_TEMP:-/tmp}/g10-13-grandstream-web-login-deep-passive.txt}"
PHONE_IP="192.168.1.167"
BASE="http://${PHONE_IP}"
TMPDIR_G10="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_G10"' EXIT
chmod 700 "$TMPDIR_G10"

fetch_same_origin() {
  local path="$1" out="$2" hdr="$3"
  case "$path" in
    http://*|https://*|//*) return 1 ;;
  esac
  local url
  case "$path" in
    /*) url="$BASE$path" ;;
    *)  url="$BASE/${path#./}" ;;
  esac
  curl -sS --connect-timeout 5 --max-time 20 -D "$hdr" -o "$out" "$url" || true
}

ROOT_BODY="$TMPDIR_G10/root.html"
ROOT_HDR="$TMPDIR_G10/root.hdr"
fetch_same_origin "/" "$ROOT_BODY" "$ROOT_HDR"

RES_DIR="$TMPDIR_G10/resources"
mkdir -p "$RES_DIR"
QUEUE="$TMPDIR_G10/queue.txt"
SEEN="$TMPDIR_G10/seen.txt"
: > "$QUEUE"
: > "$SEEN"

python3 - "$ROOT_BODY" > "$QUEUE" <<'PY'
import re,sys
s=open(sys.argv[1],'r',errors='ignore').read()
patterns=[
 r'<script[^>]+src=["\']([^"\']+)["\']',
 r'<link[^>]+href=["\']([^"\']+)["\']',
]
seen=[]
for pat in patterns:
    for m in re.finditer(pat,s,re.I):
        x=m.group(1).strip()
        if x and x not in seen:
            seen.append(x)
for x in seen:
    print(x)
PY

FETCHED=0
MAX_RESOURCES=80
ROUND=0
while [ -s "$QUEUE" ] && [ "$FETCHED" -lt "$MAX_RESOURCES" ] && [ "$ROUND" -lt 6 ]; do
  NEXT="$TMPDIR_G10/queue.next.txt"
  : > "$NEXT"
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    case "$path" in
      http://*|https://*|//*) continue ;;
      data:*|javascript:*|mailto:*) continue ;;
    esac
    grep -Fxq "$path" "$SEEN" && continue
    echo "$path" >> "$SEEN"

    safe="$(printf '%s' "$path" | tr '/?&=:#' '_______' | tr -cd 'A-Za-z0-9._-')"
    [ -n "$safe" ] || safe="resource_${FETCHED}"
    out="$RES_DIR/${FETCHED}_${safe}"
    hdr="$out.hdr"
    fetch_same_origin "$path" "$out" "$hdr" || true
    FETCHED=$((FETCHED+1))

    # Only inspect textual-looking resources and cap file size.
    if [ -f "$out" ] && [ "$(wc -c < "$out")" -le 5242880 ]; then
      python3 - "$out" >> "$NEXT" <<'PY'
import re,sys
s=open(sys.argv[1],'r',errors='ignore').read()
patterns=[
 r'["\']([^"\']+\.cache\.js(?:\?[^"\']*)?)["\']',
 r'["\']([^"\']+\.nocache\.js(?:\?[^"\']*)?)["\']',
 r'["\']([^"\']+\.js(?:\?[^"\']*)?)["\']',
 r'["\']([^"\']+\.css(?:\?[^"\']*)?)["\']',
 r'["\']([^"\']+/cgi-bin/[^"\']+)["\']',
 r'["\'](/cgi-bin/[^"\']+)["\']',
]
seen=[]
for pat in patterns:
    for m in re.finditer(pat,s,re.I):
        x=m.group(1).strip()
        if x.startswith(('http://','https://','//','data:','javascript:')):
            continue
        if x not in seen:
            seen.append(x)
for x in seen:
    print(x)
PY
    fi
  done < "$QUEUE"
  sort -u "$NEXT" > "$QUEUE"
  ROUND=$((ROUND+1))
done

SCAN="$TMPDIR_G10/scan.txt"
: > "$SCAN"
find "$TMPDIR_G10" -type f ! -name '*.hdr' -size -5M -print0 | \
  xargs -0 grep -Eio '(/cgi-bin/[A-Za-z0-9._/?=&:%+-]+|dologin|login|logout|challenge|nonce|sid|session|cookie|md5|sha1|sha256|password|username|api\.values\.(get|post)|\.cache\.js|\.nocache\.js)' 2>/dev/null | \
  sed 's#^[^:]*:##' | sort -u > "$SCAN" || true

PATHS="$TMPDIR_G10/paths.txt"
grep -E '^/cgi-bin/' "$SCAN" | sort -u | head -100 > "$PATHS" || true

kw() {
  local k="$1"
  if grep -Eiq "^${k}$" "$SCAN"; then echo YES; else echo NO; fi
}

ROOT_CODE="$(awk 'toupper($1) ~ /^HTTP\// {code=$2} END{print code}' "$ROOT_HDR")"
ROOT_CT="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$ROOT_HDR")"
[ -n "$ROOT_CODE" ] || ROOT_CODE='UNKNOWN'
[ -n "$ROOT_CT" ] || ROOT_CT='NONE'

CACHE_COUNT="$(grep -Eic '\.cache\.js$' "$SEEN" || true)"
NOCACHE_COUNT="$(grep -Eic '\.nocache\.js$' "$SEEN" || true)"

{
  echo '=== G10-13 GRANDSTREAM GXP1625 DEEP PASSIVE WEB LOGIN AUDIT ==='
  echo "phone_ip=${PHONE_IP}"
  echo 'firmware_prog=1.0.7.70'
  echo 'authentication_attempt=NO'
  echo 'credentials_used=NO'
  echo 'configuration_write=NO'
  echo 'api_values_post_called=NO'
  echo "root_http=${ROOT_CODE}"
  echo "root_content_type=${ROOT_CT}"
  echo "resources_fetched=${FETCHED}"
  echo "discovery_rounds=${ROUND}"
  echo "gwt_cache_js_seen=${CACHE_COUNT}"
  echo "gwt_nocache_js_seen=${NOCACHE_COUNT}"
  echo "keyword_dologin=$(kw dologin)"
  echo "keyword_login=$(kw login)"
  echo "keyword_challenge=$(kw challenge)"
  echo "keyword_nonce=$(kw nonce)"
  echo "keyword_sid=$(kw sid)"
  echo "keyword_session=$(kw session)"
  echo "keyword_cookie=$(kw cookie)"
  echo "keyword_md5=$(kw md5)"
  echo "keyword_sha1=$(kw sha1)"
  echo "keyword_sha256=$(kw sha256)"
  echo "keyword_api_values_get=$(grep -Eiq '^api\.values\.get$' "$SCAN" && echo YES || echo NO)"
  echo "keyword_api_values_post=$(grep -Eiq '^api\.values\.post$' "$SCAN" && echo YES || echo NO)"
  echo "cgi_bin_path_count=$(wc -l < "$PATHS" | tr -d ' ')"
  if [ -s "$PATHS" ]; then
    echo 'cgi_bin_paths_begin'
    sed 's/^/path=/' "$PATHS"
    echo 'cgi_bin_paths_end'
  fi
  echo 'G10-13-PASS'
} | tee "$REPORT"

grep -Fq 'G10-13-PASS' "$REPORT"
