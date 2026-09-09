#!/usr/bin/env python3
"""G10-17D: read-only cookie/session sequence diagnostic for GXP1625.

LAB only. Reproduces the authenticated browser-like sequence without any
configuration write. It records only whether Set-Cookie appears after each
read/status request; cookie values, SID, and password are never printed.
"""
import http.client
import json
import os
import sys
import urllib.parse

PHONE_IP = "192.168.1.167"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17d-session-cookie-sequence.txt"

if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")


def post(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    r = conn.getresponse()
    raw = r.read()
    return r.status, r.getheaders(), raw


def parse_json(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def cookie_pairs_from(headers):
    pairs = []
    for name, value in headers:
        if name.lower() == "set-cookie":
            pair = value.split(";", 1)[0].strip()
            if pair and "=" in pair:
                pairs.append(pair)
    return pairs


def merge_cookie_pairs(current, new_pairs):
    by_name = {}
    for pair in current + new_pairs:
        name = pair.split("=", 1)[0]
        by_name[name] = pair
    return list(by_name.values())

base_headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": PHONE_IP,
    "Origin": "http://%s" % PHONE_IP,
    "Referer": "http://%s/" % PHONE_IP,
}

conn = http.client.HTTPConnection(PHONE_IP, timeout=10)
login_http, login_headers, login_raw = post(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": PASSWORD},
    dict(base_headers),
)
login_json = parse_json(login_raw)
login_response = str(login_json.get("response", "")) or "EMPTY"
sid = ""
if isinstance(login_json.get("body"), dict):
    sid = str(login_json["body"].get("sid") or "")

cookies = cookie_pairs_from(login_headers)
login_cookie_count = len(cookies)

results = []

def run_step(label, path, form):
    global cookies
    headers = dict(base_headers)
    if cookies:
        headers["Cookie"] = "; ".join(cookies)
    http, resp_headers, raw = post(conn, path, form, headers)
    new = cookie_pairs_from(resp_headers)
    cookies = merge_cookie_pairs(cookies, new)
    data = parse_json(raw)
    response = str(data.get("response", "")) or "EMPTY"
    status = "NONE"
    if isinstance(data.get("body"), dict):
        status = str(data["body"].get("status", "")) or "NONE"
    results.append((label, http, response, status, len(new), len(cookies)))

if login_http == 200 and login_response == "success" and sid:
    run_step("values_get_1", "/cgi-bin/api.values.get", {"request": "P35:P208", "sid": sid})
    run_step("phone_status", "/cgi-bin/api-get_phone_status", {"sid": sid})
    run_step("values_get_2", "/cgi-bin/api.values.get", {"request": "P35:P208", "sid": sid})

diagnostic = "LOGIN_FAILED"
if login_http == 200 and login_response == "success" and sid:
    if cookies:
        diagnostic = "COOKIE_AVAILABLE_AFTER_SEQUENCE"
    else:
        diagnostic = "NO_COOKIE_AFTER_SEQUENCE"

lines = [
    "=== G10-17D GRANDSTREAM SESSION COOKIE SEQUENCE DIAGNOSTIC ===",
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
    "login_response=%s" % login_response,
    "sid_present=%s" % ("YES" if sid else "NO"),
    "login_set_cookie_count=%d" % login_cookie_count,
]
for label, http, response, status, new_cookie_count, total_cookie_count in results:
    lines.extend([
        "%s_http=%s" % (label, http),
        "%s_response=%s" % (label, response),
        "%s_status=%s" % (label, status),
        "%s_new_set_cookie_count=%d" % (label, new_cookie_count),
        "%s_total_cookie_count=%d" % (label, total_cookie_count),
    ])
lines.extend([
    "final_cookie_present=%s" % ("YES" if cookies else "NO"),
    "final_cookie_count=%d" % len(cookies),
    "diagnostic=%s" % diagnostic,
    "G10-17D-COMPLETE",
])

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
for line in lines:
    print(line)
