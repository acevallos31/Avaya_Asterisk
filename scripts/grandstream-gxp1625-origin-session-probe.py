#!/usr/bin/env python3
"""G10-17A: controlled GXP1625 browser-shape session probe.

LAB only. Authenticates to the physical phone, confirms P208 is still the
expected value, then POSTs that same value back through api.values.post using
Host + Origin + Referer + Cookie + SID. Secret values are never printed.
"""
import http.client
import json
import os
import sys
import urllib.parse

PHONE_IP = "192.168.1.167"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
EXPECTED_P208 = "2"
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17a-grandstream-origin-session-probe.txt"

if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")


def request(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    ctype = response.getheader("Content-Type", "")
    return response.status, ctype, response.getheaders(), raw


def parse_json(raw, label):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise SystemExit("ERROR: %s no devolvió JSON válido" % label)


base_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": PHONE_IP,
    "Origin": "http://%s" % PHONE_IP,
    "Referer": "http://%s/" % PHONE_IP,
}

conn = http.client.HTTPConnection(PHONE_IP, timeout=10)

login_http, login_ct, login_headers, login_raw = request(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": PASSWORD},
    dict(base_headers),
)
login_json = parse_json(login_raw, "dologin")
login_ok = login_http == 200 and login_json.get("response") == "success"
sid = ""
if isinstance(login_json.get("body"), dict):
    sid = str(login_json["body"].get("sid") or "")

cookie_pairs = []
cookie_names = []
for name, value in login_headers:
    if name.lower() == "set-cookie":
        pair = value.split(";", 1)[0].strip()
        if pair and "=" in pair:
            cookie_pairs.append(pair)
            cookie_names.append(pair.split("=", 1)[0])

if not login_ok or not sid:
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("=== G10-17A GRANDSTREAM ORIGIN SESSION PROBE ===\n")
        fh.write("login_http=%s\n" % login_http)
        fh.write("login_json_success=NO\n")
        fh.write("sid_present=%s\n" % ("YES" if sid else "NO"))
        fh.write("credential_value_logged=NO\n")
        fh.write("session_values_logged=NO\n")
        fh.write("probe_result=LOGIN_FAILED\n")
        fh.write("G10-17A-COMPLETE\n")
    print("login_http=%s" % login_http)
    print("login_json_success=NO")
    print("sid_present=%s" % ("YES" if sid else "NO"))
    print("probe_result=LOGIN_FAILED")
    print("G10-17A-COMPLETE")
    raise SystemExit(0)

session_headers = dict(base_headers)
if cookie_pairs:
    session_headers["Cookie"] = "; ".join(cookie_pairs)

get_http, get_ct, _, get_raw = request(
    conn,
    "/cgi-bin/api.values.get",
    {"request": "P208", "sid": sid},
    session_headers,
)
get_json = parse_json(get_raw, "api.values.get")
current_p208 = ""
if isinstance(get_json.get("body"), dict):
    current_p208 = str(get_json["body"].get("P208", ""))

post_http = "SKIPPED"
post_ct = "SKIPPED"
post_response = "SKIPPED"
post_status = "SKIPPED"
probe_result = "PRECONDITION_FAILED"

if get_http == 200 and current_p208 == EXPECTED_P208:
    post_http, post_ct, _, post_raw = request(
        conn,
        "/cgi-bin/api.values.post",
        {"P208": EXPECTED_P208, "sid": sid},
        session_headers,
    )
    post_json = parse_json(post_raw, "api.values.post")
    post_response = str(post_json.get("response", ""))
    if isinstance(post_json.get("body"), dict):
        post_status = str(post_json["body"].get("status", ""))
    if post_http == 200 and post_response == "success":
        probe_result = "ORIGIN_BROWSER_SHAPE_ACCEPTED"
    elif post_status == "session-expired":
        probe_result = "ORIGIN_NOT_SUFFICIENT_SESSION_EXPIRED"
    else:
        probe_result = "ORIGIN_BROWSER_SHAPE_REJECTED"

lines = [
    "=== G10-17A GRANDSTREAM ORIGIN SESSION PROBE ===",
    "phone_ip=%s" % PHONE_IP,
    "firmware_prog=1.0.7.70",
    "db_write=NO",
    "live_code_write=NO",
    "phone_write=IDEMPOTENT-P208-SAME-VALUE-ONLY",
    "credential_source=GITHUB-ACTIONS-SECRET",
    "credential_value_logged=NO",
    "session_values_logged=NO",
    "origin_sent=YES",
    "host_sent=YES",
    "referer_sent=YES",
    "login_http=%s" % login_http,
    "login_json_success=YES",
    "sid_present=YES",
    "cookie_present=%s" % ("YES" if cookie_pairs else "NO"),
    "cookie_name_count=%d" % len(set(cookie_names)),
    "read_p208_http=%s" % get_http,
    "read_p208_value=%s" % (current_p208 if current_p208 else "EMPTY"),
    "precondition_p208_expected=%s" % EXPECTED_P208,
    "post_http=%s" % post_http,
    "post_response=%s" % post_response,
    "post_status=%s" % post_status,
    "probe_result=%s" % probe_result,
    "G10-17A-COMPLETE",
]

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

for line in lines:
    print(line)
