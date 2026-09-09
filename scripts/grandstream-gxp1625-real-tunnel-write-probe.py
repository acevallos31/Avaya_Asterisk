#!/usr/bin/env python3
"""G10-17G: controlled GXP1625 write probe through the real HTTPS tunnel.

Unlike G10-17E/F, this does NOT connect directly to 192.168.1.167 while only
spoofing Host/Origin/Referer. It connects to phone1.nocpbx.com:443 using TLS,
matching the successful browser transport path. It reads P208 and only posts
the exact same current value back. No password, SID, cookie, or P208 value is
printed.
"""
import http.client
import json
import os
import ssl
import sys
import urllib.parse

HOST = "phone1.nocpbx.com"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17g-real-tunnel-write-probe.txt"

if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"


def base_headers():
    return {
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://%s" % HOST,
        "Referer": "https://%s/" % HOST,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": UA,
    }


def req(conn, path, form, headers):
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


def cookie_pairs(headers):
    pairs = []
    for name, value in headers:
        if name.lower() == "set-cookie":
            pair = value.split(";", 1)[0].strip()
            if pair and "=" in pair:
                pairs.append(pair)
    return pairs


ctx = ssl.create_default_context()
conn = http.client.HTTPSConnection(HOST, 443, timeout=15, context=ctx)
headers = base_headers()

login_http, login_headers, login_raw = req(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": PASSWORD},
    dict(headers),
)
login_json = parse_json(login_raw)
login_response = str(login_json.get("response", "")) or "EMPTY"
sid = ""
if isinstance(login_json.get("body"), dict):
    sid = str(login_json["body"].get("sid") or "")

cookies = cookie_pairs(login_headers)
session_headers = dict(headers)
if cookies:
    session_headers["Cookie"] = "; ".join(cookies)

read_http = "SKIPPED"
read_response = "SKIPPED"
read_p208_present = "SKIPPED"
p208 = ""
post_http = "SKIPPED"
post_response = "SKIPPED"
post_status = "SKIPPED"

if login_http == 200 and login_response == "success" and sid:
    read_http, read_headers, read_raw = req(
        conn,
        "/cgi-bin/api.values.get",
        {"request": "P208", "sid": sid},
        session_headers,
    )
    # Merge only named cookies if the tunnel/phone refreshes them.
    refreshed = cookie_pairs(read_headers)
    if refreshed:
        cookies = refreshed
        session_headers["Cookie"] = "; ".join(cookies)

    read_json = parse_json(read_raw)
    read_response = str(read_json.get("response", "")) or "EMPTY"
    body = read_json.get("body")
    if isinstance(body, dict) and "P208" in body:
        read_p208_present = "YES"
        p208 = str(body.get("P208"))
    else:
        read_p208_present = "NO"

    if read_http == 200 and read_response == "success" and read_p208_present == "YES":
        post_http, post_headers, post_raw = req(
            conn,
            "/cgi-bin/api.values.post",
            {"P208": p208, "sid": sid},
            session_headers,
        )
        post_json = parse_json(post_raw)
        post_response = str(post_json.get("response", "")) or "EMPTY"
        pbody = post_json.get("body")
        if isinstance(pbody, dict):
            post_status = str(pbody.get("status", "")) or "NONE"
        else:
            post_status = "NONE"

if post_http == 200 and post_response == "success":
    diagnostic = "REAL_TUNNEL_WRITE_ACCEPTED"
elif post_status == "session-expired":
    diagnostic = "REAL_TUNNEL_WRITE_SESSION_EXPIRED"
elif login_http != 200 or login_response != "success" or not sid:
    diagnostic = "REAL_TUNNEL_LOGIN_FAILED"
elif read_response != "success" or read_p208_present != "YES":
    diagnostic = "REAL_TUNNEL_READ_FAILED"
else:
    diagnostic = "REAL_TUNNEL_WRITE_REJECTED_OTHER"

lines = [
    "=== G10-17G GRANDSTREAM REAL HTTPS TUNNEL WRITE PROBE ===",
    "transport=HTTPS_REAL_TUNNEL",
    "target_host=%s" % HOST,
    "db_write=NO",
    "live_code_write=NO",
    "phone_write=SAME-VALUE-P208-ONLY",
    "session_values_logged=NO",
    "login_http=%s" % login_http,
    "login_response=%s" % login_response,
    "sid_present=%s" % ("YES" if sid else "NO"),
    "cookie_present=%s" % ("YES" if cookies else "NO"),
    "cookie_count=%s" % len(cookies),
    "read_http=%s" % read_http,
    "read_response=%s" % read_response,
    "read_p208_present=%s" % read_p208_present,
    "post_http=%s" % post_http,
    "post_response=%s" % post_response,
    "post_status=%s" % post_status,
    "diagnostic=%s" % diagnostic,
    "G10-17G-COMPLETE",
]

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
