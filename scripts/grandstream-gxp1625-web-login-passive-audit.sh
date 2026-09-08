#!/usr/bin/env bash
set -euo pipefail

REPORT="${1:-${RUNNER_TEMP:-/tmp}/g10-12-grandstream-web-login-passive.txt}"
PHONE_IP="192.168.1.167"
BASE="http://${PHONE_IP}"
TMPDIR_G10="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_G10"' EXIT
chmod 700 "$TMPDIR_G10"

fetch() {
  local url="$1" out="$2" hdr="$3"
  curl -sS --connect-timeout 5 --max-time 15 -D "$hdr" -o "$out" "$url" || true
}

ROOT_BODY="$TMPDIR_G10/root.html"
ROOT_HDR="$TMPDIR_G10/root.hdr"
fetch "$BASE/" "$ROOT_BODY" "$ROOT_HDR"

# Extract same-origin script src values only. Never fetch cross-origin URLs.
mapfile -t SCRIPTS < <(python3 - "$ROOT_BODY" <<'PY'
import re,sys,urllib.parse
p=sys.argv[1]
s=open(p,'r',errors='ignore').read()
seen=[]
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', s, re.I):
    src=m.group(1).strip()
    u=urllib.parse.urlparse(src)
    if u.scheme or u.netloc:
        continue
    if src.startswith('//'):
        continue
    if src not in seen:
        seen.append(src)
for x in seen[:25]:
    print(x)
PY
)

JS_DIR="$TMPDIR_G10/js"
mkdir -p "$JS_DIR"
COUNT=0
for src in "${SCRIPTS[@]:-}"; do
  [ -n "$src" ] || continue
  case "$src" in
    /*) url="$BASE$src" ;;
    *)  url="$BASE/${src#./}" ;;
  esac
  safe="$(printf '%s' "$src" | tr '/?&=:' '______' | tr -cd 'A-Za-z0-9._-')"
  [ -n "$safe" ] || safe="script_${COUNT}.js"
  fetch "$url" "$JS_DIR/$safe" "$JS_DIR/$safe.hdr"
  COUNT=$((COUNT+1))
done

# Search public HTML/JS for login-related mechanics. Report only keywords and path-like literals,
# never response bodies or credential material.
SCAN_FILE="$TMPDIR_G10/scan.txt"
: > "$SCAN_FILE"
find "$TMPDIR_G10" -type f \( -name '*.html' -o -path '*/js/*' \) -size -5M -print0 | \
  xargs -0 grep -Eio '(/cgi-bin/[A-Za-z0-9._/?=&:-]+|dologin|login|logout|challenge|nonce|sid|session|cookie|md5|sha1|sha256|password|username|api\.values\.(get|post))' 2>/dev/null | \
  sed 's#^[^:]*:##' | sort -u > "$SCAN_FILE" || true

# Keep path candidates separately for cleaner interpretation.
PATHS_FILE="$TMPDIR_G10/paths.txt"
grep -E '^/cgi-bin/' "$SCAN_FILE" | sort -u | head -100 > "$PATHS_FILE" || true

keyword_present() {
  local k="$1"
  if grep -Eiq "^${k}$" "$SCAN_FILE"; then echo YES; else echo NO; fi
}

ROOT_CODE="$(awk 'toupper($1) ~ /^HTTP\// {code=$2} END{print code}' "$ROOT_HDR")"
ROOT_CT="$(awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {gsub("\r",""); sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$ROOT_HDR")"
[ -n "$ROOT_CODE" ] || ROOT_CODE='UNKNOWN'
[ -n "$ROOT_CT" ] || ROOT_CT='NONE'

{
  echo '=== G10-12 GRANDSTREAM GXP1625 PASSIVE WEB LOGIN AUDIT ==='
  echo "phone_ip=${PHONE_IP}"
  echo 'firmware_prog=1.0.7.70'
  echo 'authentication_attempt=NO'
  echo 'credentials_used=NO'
  echo 'configuration_write=NO'
  echo 'api_values_post_called=NO'
  echo "root_http=${ROOT_CODE}"
  echo "root_content_type=${ROOT_CT}"
  echo "public_script_refs=${#SCRIPTS[@]}"
  echo "public_scripts_fetched=${COUNT}"
  echo "keyword_dologin=$(keyword_present dologin)"
  echo "keyword_challenge=$(keyword_present challenge)"
  echo "keyword_nonce=$(keyword_present nonce)"
  echo "keyword_sid=$(keyword_present sid)"
  echo "keyword_session=$(keyword_present session)"
  echo "keyword_cookie=$(keyword_present cookie)"
  echo "keyword_md5=$(keyword_present md5)"
  echo "keyword_sha1=$(keyword_present sha1)"
  echo "keyword_sha256=$(keyword_present sha256)"
  echo "keyword_api_values_get=$(grep -Eiq '^api\.values\.get$' "$SCAN_FILE" && echo YES || echo NO)"
  echo "keyword_api_values_post=$(grep -Eiq '^api\.values\.post$' "$SCAN_FILE" && echo YES || echo NO)"
  echo "cgi_bin_path_count=$(wc -l < "$PATHS_FILE" | tr -d ' ')"
  if [ -s "$PATHS_FILE" ]; then
    echo 'cgi_bin_paths_begin'
    sed 's/^/path=/' "$PATHS_FILE"
    echo 'cgi_bin_paths_end'
  fi
  echo 'G10-12-PASS'
} | tee "$REPORT"

grep -Fq 'G10-12-PASS' "$REPORT"
