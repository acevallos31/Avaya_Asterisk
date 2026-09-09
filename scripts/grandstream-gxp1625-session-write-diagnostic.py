#!/usr/bin/env python3
"""G10-17C: controlled same-value GXP1625 write-session diagnostic.

LAB only. Authenticates, confirms the browser-shape session with Host + Origin +
Referer + Cookie + SID, reads P208, then writes the exact same P208 value back
through /cgi-bin/api.values.post. Secret/session values are never printed.
"""
import http.client
import json
import os
import sys
import urllib.parse

PHONE_IP = "192.168.1.167"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17c-grandstream-session-write-diagnostic.txt"

if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")


def request(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    return response.status, response.getheaders(), raw


def parse_json(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


base_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": PHONE_IP,
    "Origin": "http://%s" % PHONE_IP,
    "Referer": "http://%s/" % PHONE_IP,
}

conn = http.client.HTTPConnection(PHONE_IP, timeout=10)
login_http, login_headers, login_raw = request(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": PASSWORD},
    dict(base_headers),
)
login_json = parse_json(login_raw)
login_response = str(login_json.get("response", ""))
sid = ""
if isinstance(login_json.get("body"), dict):
    sid = str(login_json["body"].get("sid") or "")

cookie_pairs = []
for name, value in login_headers:
    if name.lower() == "set-cookie":
        pair = value.split(";", 1)[0].strip()
        if pair and "=" in pair:
            cookie_pairs.append(pair)

session_headers = dict(base_headers)
if cookie_pairs:
    session_headers["Cookie"] = "; ".join(cookie_pairs)

read_http = "SKIPPED"
read_response = "SKIPPED"
read_p208_present = "NO"
current_p208 = None
post_http = "SKIPPED"
post_response = "SKIPPED"
post_status = "SKIPPED"
diagnostic = "LOGIN_FAILED"

if login_http == 200 and login_response == "success" and sid:
    read_http, _, read_raw = request(
        conn,
        "/cgi-bin/api.values.get",
        {"request": "P208", "sid": sid},
        session_headers,
    )
    read_json = parse_json(read_raw)
    read_response = str(read_json.get("response", "")) or "EMPTY"
    body = read_json.get("body")
    if isinstance(body, dict) and "P208" in body:
        current_p208 = str(body.get("P208", ""))
        read_p208_present = "YES"

    if read_http != 200:
        diagnostic = "READ_HTTP_FAILED"
    elif read_response != "success":
        diagnostic = "READ_SESSION_REJECTED"
    elif current_p208 is None:
        diagnostic = "READ_VALUE_MISSING"
    else:
        post_http, _, post_raw = request(
            conn,
            "/cgi-bin/api.values.post",
            {"P208": current_p208, "sid": sid},
            session_headers,
        )
        post_json = parse_json(post_raw)
        post_response = str(post_json.get("response", "")) or "EMPTY"
        if isinstance(post_json.get("body"), dict):
            post_status = str(post_json["body"].get("status", "")) or "NONE"
        if post_http == 200 and post_response == "success":
            diagnostic = "WRITE_SESSION_ACCEPTED"
        elif post_status == "session-expired":
            diagnostic = "WRITE_SESSION_EXPIRED"
        else:
            diagnostic = "WRITE_REJECTED_OTHER"

lines = [
    "=== G10-17C GRANDSTREAM SESSION WRITE DIAGNOSTIC ===",
    "phone_ip=%s" % PHONE_IP,
    "firmware_prog=1.0.7.70",
    "db_write=NO",
    "live_code_write=NO",
    "phone_write=SAME-VALUE-P208-ONLY",
    "credential_value_logged=NO",
    "session_values_logged=NO",
    "origin_sent=YES",
    "host_sent=YES",
    "referer_sent=YES",
    "login_http=%s" % login_http,
    "login_response=%s" % (login_response or "EMPTY"),
    "sid_present=%s" % ("YES" if sid else "NO"),
    "cookie_present=%s" % ("YES" if cookie_pairs else "NO"),
    "cookie_pair_count=%d" % len(cookie_pairs),
    "read_request=P208",
    "read_http=%s" % read_http,
    "read_response=%s" % read_response,
    "read_p208_present=%s" % read_p208_present,
    "same_value_write_precondition=%s" % ("PASS" if current_p208 is not None else "FAIL"),
    "post_http=%s" % post_http,
    "post_response=%s" % post_response,
    "post_status=%s" % post_status,
    "diagnostic=%s" % diagnostic,
    "G10-17C-COMPLETE",
]

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

for line in lines:
    print(line)
