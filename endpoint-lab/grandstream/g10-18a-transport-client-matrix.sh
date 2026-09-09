#!/usr/bin/env bash
set -euo pipefail

PHONE_IP="${PHONE_IP:-192.168.1.167}"
TUNNEL_HOST="${TUNNEL_HOST:-phone1.nocpbx.com}"
USERNAME="${GRANDSTREAM_HTTP_USERNAME:-admin}"
PASSWORD="${GRANDSTREAM_HTTP_PASSWORD:-}"
REPORT="${1:-g10-18a-transport-client-matrix.txt}"
COLLECTION="${COLLECTION:-endpoint-lab/grandstream/gxp1625.postman_collection.json}"

if [ -z "$PASSWORD" ]; then
  echo "ERROR: GRANDSTREAM_HTTP_PASSWORD missing" >&2
  exit 2
fi

TMP="$(mktemp -d)"
chmod 700 "$TMP"
trap 'rm -rf "$TMP"' EXIT
: > "$REPORT"
chmod 600 "$REPORT"

log() { printf '%s\n' "$1" | tee -a "$REPORT"; }

json_field() {
  local file="$1" expr="$2"
  jq -r "$expr // empty" "$file" 2>/dev/null || true
}

urlencode_sid_form() {
  local prefix="$1" sid="$2"
  printf '%s' "$sid" | python3 -c 'import sys,urllib.parse; s=sys.stdin.read(); print(urllib.parse.urlencode({"request":"P208","sid":s}))' > "$prefix"
}

urlencode_write_form() {
  local out="$1" p208="$2" sid="$3"
  { printf '%s\0%s' "$p208" "$sid"; } | python3 -c 'import sys,urllib.parse; d=sys.stdin.buffer.read().split(b"\0",1); print(urllib.parse.urlencode({"P208":d[0].decode(),"sid":d[1].decode()}))' > "$out"
}

run_curl_variant() {
  local name="$1" base="$2" proto="$3"
  local origin="$base" referer="$base/"
  local login_body="$TMP/${name}.login.body" login_hdr="$TMP/${name}.login.hdr" cookie="$TMP/${name}.cookie"
  local read_body="$TMP/${name}.read.body" read_hdr="$TMP/${name}.read.hdr"
  local post_body="$TMP/${name}.post.body" post_hdr="$TMP/${name}.post.hdr"
  local login_form="$TMP/${name}.login.form" read_form="$TMP/${name}.read.form" write_form="$TMP/${name}.write.form"
  chmod 600 "$login_body" "$login_hdr" "$cookie" "$read_body" "$read_hdr" "$post_body" "$post_hdr" "$login_form" "$read_form" "$write_form" 2>/dev/null || true

  printf 'username=%s&password=' "$(printf '%s' "$USERNAME" | jq -sRr @uri)" > "$login_form"
  printf '%s' "$PASSWORD" | jq -sRr @uri >> "$login_form"

  local meta rc
  set +e
  meta=$(curl -sS $proto --connect-timeout 5 --max-time 20 \
    -D "$login_hdr" -c "$cookie" -o "$login_body" \
    -w '%{http_code}|%{http_version}' \
    -H 'Accept: */*' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H "Origin: $origin" -H "Referer: $referer" \
    --data-binary @"$login_form" "$base/cgi-bin/dologin" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=TRANSPORT_FAILED|curl_rc=$rc"
    return
  fi

  local login_http="${meta%%|*}" login_ver="${meta#*|}"
  local login_resp sid
  login_resp=$(json_field "$login_body" '.response')
  sid=$(json_field "$login_body" '.body.sid')
  if [ "$login_http" != "200" ] || [ "$login_resp" != "success" ] || [ -z "$sid" ]; then
    log "$name=LOGIN_FAILED|http=$login_http|http_version=$login_ver|response=${login_resp:-EMPTY}|sid_present=$( [ -n "$sid" ] && echo YES || echo NO )"
    return
  fi

  urlencode_sid_form "$read_form" "$sid"
  set +e
  meta=$(curl -sS $proto --connect-timeout 5 --max-time 20 \
    -D "$read_hdr" -b "$cookie" -c "$cookie" -o "$read_body" \
    -w '%{http_code}|%{http_version}' \
    -H 'Accept: */*' -H 'Content-Type: application/x-www-form-urlencoded' \
    -H "Origin: $origin" -H "Referer: $referer" \
    --data-binary @"$read_form" "$base/cgi-bin/api.values.get" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=READ_TRANSPORT_FAILED|curl_rc=$rc|login_http_version=$login_ver"
    return
  fi

  local read_http="${meta%%|*}" read_ver="${meta#*|}" read_resp p208
  read_resp=$(json_field "$read_body" '.response')
  p208=$(json_field "$read_body" '.body.P208')
  if [ "$read_http" != "200" ] || [ "$read_resp" != "success" ] || [ -z "$p208" ]; then
    log "$name=READ_FAILED|login_http_version=$login_ver|read_http=$read_http|read_http_version=$read_ver|read_response=${read_resp:-EMPTY}|p208_present=$( [ -n "$p208" ] && echo YES || echo NO )"
    return
  fi

  urlencode_write_form "$write_form" "$p208" "$sid"
  set +e
  meta=$(curl -sS $proto --connect-timeout 5 --max-time 20 \
    -D "$post_hdr" -b "$cookie" -c "$cookie" -o "$post_body" \
    -w '%{http_code}|%{http_version}' \
    -H 'Accept: */*' -H 'Content-Type: application/x-www-form-urlencoded' \
    -H "Origin: $origin" -H "Referer: $referer" \
    --data-binary @"$write_form" "$base/cgi-bin/api.values.post" 2>/dev/null)
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "$name=WRITE_TRANSPORT_FAILED|curl_rc=$rc|read_http_version=$read_ver"
    return
  fi

  local post_http="${meta%%|*}" post_ver="${meta#*|}" post_resp post_status result
  post_resp=$(json_field "$post_body" '.response')
  post_status=$(json_field "$post_body" '.body.status')
  result="WRITE_REJECTED_OTHER"
  if [ "$post_http" = "200" ] && [ "$post_resp" = "success" ]; then result="WRITE_ACCEPTED"; fi
  if [ "$post_status" = "session-expired" ]; then result="WRITE_SESSION_EXPIRED"; fi
  log "$name=$result|login_http_version=$login_ver|read_http_version=$read_ver|post_http=$post_http|post_http_version=$post_ver|post_response=${post_resp:-EMPTY}|post_status=${post_status:-EMPTY}"
}

run_newman_variant() {
  local name="$1" base="$2"
  local envf="$TMP/${name}.environment.json" raw="$TMP/${name}.newman.json"
  local origin="$base" referer="$base/"
  jq -n \
    --arg base "$base" --arg origin "$origin" --arg referer "$referer" \
    --arg user "$USERNAME" --arg pass "$PASSWORD" \
    '{id:"g10-18a",name:"G10-18A ephemeral",values:[
      {key:"base_url",value:$base,enabled:true},
      {key:"origin",value:$origin,enabled:true},
      {key:"referer",value:$referer,enabled:true},
      {key:"http_username",value:$user,enabled:true},
      {key:"http_password",value:$pass,enabled:true},
      {key:"sid",value:"",enabled:true},
      {key:"p208_current",value:"",enabled:true}
    ],_postman_variable_scope:"environment",_postman_exported_at:"2026-09-09T00:00:00.000Z",_postman_exported_using:"endpoint-lab"}' > "$envf"
  chmod 600 "$envf"
  set +e
  newman run "$COLLECTION" -e "$envf" -r json --reporter-json-export "$raw" >/dev/null 2>&1
  local rc=$?
  set -e
  local assertions failures requests
  assertions=$(jq -r '.run.stats.assertions.total // 0' "$raw" 2>/dev/null || echo 0)
  failures=$(jq -r '.run.failures | length' "$raw" 2>/dev/null || echo 0)
  requests=$(jq -r '.run.stats.requests.total // 0' "$raw" 2>/dev/null || echo 0)
  log "$name=NEWMAN_COMPLETE|exit_code=$rc|requests=$requests|assertions=$assertions|failures=$failures"
}

log '=== G10-18A ENDPOINT LAB TRANSPORT / CLIENT MATRIX ==='
log 'db_write=NO'
log 'live_pbx_code_write=NO'
log 'phone_write=SAME-VALUE-P208-ONLY_AFTER_SUCCESSFUL_READ'
log 'credential_values_logged=NO'
log 'session_values_logged=NO'
log 'runner_role=DEDICATED_ENDPOINT_LAB'

run_curl_variant 'curl_lan_http11' "http://$PHONE_IP" '--http1.1'
run_curl_variant 'curl_tunnel_http11' "https://$TUNNEL_HOST" '--http1.1'
run_curl_variant 'curl_tunnel_http2' "https://$TUNNEL_HOST" '--http2'
run_curl_variant 'curl_tunnel_http3' "https://$TUNNEL_HOST" '--http3'
run_newman_variant 'newman_lan' "http://$PHONE_IP"
run_newman_variant 'newman_tunnel' "https://$TUNNEL_HOST"

log 'G10-18A-COMPLETE'
