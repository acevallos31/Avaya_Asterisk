#!/usr/bin/env python3
"""G10-17H: GXP1625 cookie lifecycle matrix.

LAB only. Authenticates directly to the phone, performs an authenticated read,
tracks Set-Cookie lifecycle without logging cookie values, then attempts one
same-value P208 write using the freshest observed cookie set.
"""
import http.client
import json
import os
import sys
import urllib.parse

PHONE_IP = "192.168.1.167"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17h-cookie-lifecycle-matrix.txt"

if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")


def req(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    r = conn.getresponse()
    raw = r.read()
    return r.status, r.getheaders(), raw


def js(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def cookie_pairs(headers):
    out = []
    for n, v in headers:
        if n.lower() == "set-cookie":
            pair = v.split(";", 1)[0].strip()
            if pair and "=" in pair:
                out.append(pair)
    return out


def merge_cookies(current, new_pairs):
    jar = {}
    for pair in current + new_pairs:
        name, value = pair.split("=", 1)
        jar[name] = value
    return ["%s=%s" % (k, v) for k, v in jar.items()]


headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": PHONE_IP,
    "Origin": "http://%s" % PHONE_IP,
    "Referer": "http://%s/" % PHONE_IP,
    "Accept": "*/*",
}

conn = http.client.HTTPConnection(PHONE_IP, timeout=10)

lhttp, lhdrs, lraw = req(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": PASSWORD},
    dict(headers),
)
lj = js(lraw)
lresp = str(lj.get("response", "")) or "EMPTY"
sid = ""
if isinstance(lj.get("body"), dict):
    sid = str(lj["body"].get("sid") or "")

login_new = cookie_pairs(lhdrs)
cookies = merge_cookies([], login_new)

read_http = read_response = read_p208_present = "SKIPPED"
read_new_count = 0
read_cookie_changed = "NO"
p208 = ""

if lhttp == 200 and lresp == "success" and sid:
    rh = dict(headers)
    if cookies:
        rh["Cookie"] = "; ".join(cookies)
    before = list(cookies)
    read_http, rhdrs, rraw = req(
        conn,
        "/cgi-bin/api.values.get",
        {"request": "P35:P208", "sid": sid},
        rh,
    )
    rj = js(rraw)
    read_response = str(rj.get("response", "")) or "EMPTY"
    body = rj.get("body")
    if isinstance(body, dict) and "P208" in body:
        read_p208_present = "YES"
        p208 = str(body.get("P208"))
    else:
        read_p208_present = "NO"
    read_new = cookie_pairs(rhdrs)
    read_new_count = len(read_new)
    cookies = merge_cookies(cookies, read_new)
    read_cookie_changed = "YES" if cookies != before else "NO"

post_http = post_response = post_status = "SKIPPED"
post_new_count = 0
post_cookie_changed = "NO"

if (
    read_http == 200
    and read_response == "success"
    and read_p208_present == "YES"
):
    ph = dict(headers)
    if cookies:
        ph["Cookie"] = "; ".join(cookies)
    before = list(cookies)
    post_http, phdrs, praw = req(
        conn,
        "/cgi-bin/api.values.post",
        {"P208": p208, "sid": sid},
        ph,
    )
    pj = js(praw)
    post_response = str(pj.get("response", "")) or "EMPTY"
    body = pj.get("body")
    post_status = str(body.get("status", "")) if isinstance(body, dict) else ""
    post_status = post_status or "NONE"
    post_new = cookie_pairs(phdrs)
    post_new_count = len(post_new)
    cookies = merge_cookies(cookies, post_new)
    post_cookie_changed = "YES" if cookies != before else "NO"

if post_http == 200 and post_response == "success":
    diagnostic = "WRITE_ACCEPTED_WITH_LATEST_COOKIE"
elif post_status == "session-expired":
    if read_cookie_changed == "YES":
        diagnostic = "COOKIE_ROTATED_BUT_WRITE_EXPIRED"
    else:
        diagnostic = "COOKIE_DID_NOT_ROTATE_AND_WRITE_EXPIRED"
elif lhttp != 200 or lresp != "success" or not sid:
    diagnostic = "LOGIN_FAILED"
elif read_response != "success" or read_p208_present != "YES":
    diagnostic = "READ_FAILED"
else:
    diagnostic = "WRITE_REJECTED_OTHER"

lines = [
    "=== G10-17H GRANDSTREAM COOKIE LIFECYCLE MATRIX ===",
    "db_write=NO",
    "live_code_write=NO",
    "phone_write=SAME-VALUE-P208-ONLY",
    "session_values_logged=NO",
    "login_http=%s" % lhttp,
    "login_response=%s" % lresp,
    "sid_present=%s" % ("YES" if sid else "NO"),
    "login_set_cookie_count=%s" % len(login_new),
    "cookie_count_after_login=%s" % len(cookies if read_http == "SKIPPED" else merge_cookies([], login_new)),
    "read_http=%s" % read_http,
    "read_response=%s" % read_response,
    "read_p208_present=%s" % read_p208_present,
    "read_new_set_cookie_count=%s" % read_new_count,
    "read_cookie_changed=%s" % read_cookie_changed,
    "cookie_count_before_post=%s" % len(cookies),
    "post_http=%s" % post_http,
    "post_response=%s" % post_response,
    "post_status=%s" % post_status,
    "post_new_set_cookie_count=%s" % post_new_count,
    "post_cookie_changed=%s" % post_cookie_changed,
    "diagnostic=%s" % diagnostic,
    "G10-17H-COMPLETE",
]

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
