#!/usr/bin/env python3
"""G10-17B: read-only GXP1625 browser-shape session diagnostic.

LAB only. Authenticates to the physical phone and performs a read-only
api.values.get using the same Host + Origin + Referer + Cookie + SID shape
observed in the browser. Secret/session values are never printed.
"""
import http.client
import json
import os
import sys
import urllib.parse

PHONE_IP = "192.168.1.167"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17b-grandstream-session-read-diagnostic.txt"

if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")


def request(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    return response.status, response.getheader("Content-Type", ""), response.getheaders(), raw


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
login_http, _, login_headers, login_raw = request(
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
read_status = "SKIPPED"
read_p35_present = "NO"
read_p208_present = "NO"
read_p35_value = "REDACTED"
read_p208_value = "REDACTED"

if login_http == 200 and login_response == "success" and sid:
    read_http, _, _, read_raw = request(
        conn,
        "/cgi-bin/api.values.get",
        {"request": "P35:P208", "sid": sid},
        session_headers,
    )
    read_json = parse_json(read_raw)
    read_response = str(read_json.get("response", "")) or "EMPTY"
    body = read_json.get("body")
    if isinstance(body, dict):
        read_status = str(body.get("status", "")) or "NONE"
        if "P35" in body:
            read_p35_present = "YES"
            read_p35_value = "PRESENT"
        if "P208" in body:
            read_p208_present = "YES"
            read_p208_value = "PRESENT"

if login_http != 200 or login_response != "success" or not sid:
    diagnostic = "LOGIN_FAILED"
elif read_http != 200:
    diagnostic = "READ_HTTP_FAILED"
elif read_response == "success":
    diagnostic = "READ_SESSION_ACCEPTED"
elif read_status == "session-expired":
    diagnostic = "READ_SESSION_EXPIRED"
else:
    diagnostic = "READ_REJECTED_OTHER"

lines = [
    "=== G10-17B GRANDSTREAM SESSION READ DIAGNOSTIC ===",
    "phone_ip=%s" % PHONE_IP,
    "firmware_prog=1.0.7.70",
    "db_write=NO",
    "live_code_write=NO",
    "phone_write=NO",
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
    "read_request=P35:P208",
    "read_http=%s" % read_http,
    "read_response=%s" % read_response,
    "read_status=%s" % read_status,
    "read_p35_present=%s" % read_p35_present,
    "read_p208_present=%s" % read_p208_present,
    "diagnostic=%s" % diagnostic,
    "G10-17B-COMPLETE",
]

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

for line in lines:
    print(line)
