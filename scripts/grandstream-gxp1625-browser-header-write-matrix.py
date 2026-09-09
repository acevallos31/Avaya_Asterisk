#!/usr/bin/env python3
"""G10-17F: controlled GXP1625 browser-header write matrix.

LAB only. Reproduces the successful browser request metadata observed in Chrome
for /cgi-bin/api.values.post. Two independently authenticated cases are tested
against the physical phone while connecting directly to its LAN IP:
A) browser headers without Cookie
B) same browser headers plus Cookie when dologin returns one
Each case reads P208 first and only posts the exact same current value back.
No password, SID or cookie value is printed.
"""
import http.client, json, os, sys, urllib.parse

PHONE_IP = "192.168.1.167"
HOST = "phone1.nocpbx.com"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17f-browser-header-write-matrix.txt"
if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"

def req(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    r = conn.getresponse(); raw = r.read()
    return r.status, r.getheaders(), raw

def js(raw):
    try: return json.loads(raw.decode("utf-8"))
    except Exception: return {}

def base_headers():
    return {
        "Host": HOST,
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

def run_case(label, send_cookie):
    headers = base_headers()
    conn = http.client.HTTPConnection(PHONE_IP, timeout=10)
    lhttp, lhdrs, lraw = req(conn, "/cgi-bin/dologin", {"username": USERNAME, "password": PASSWORD}, dict(headers))
    lj = js(lraw); lresp = str(lj.get("response", "")) or "EMPTY"
    sid = ""
    if isinstance(lj.get("body"), dict): sid = str(lj["body"].get("sid") or "")
    cookies = []
    for n,v in lhdrs:
        if n.lower() == "set-cookie":
            pair = v.split(";",1)[0].strip()
            if pair and "=" in pair: cookies.append(pair)
    sh = dict(headers)
    if send_cookie and cookies:
        sh["Cookie"] = "; ".join(cookies)

    rhttp=rresp=rpresent="SKIPPED"; p208=""; phttp=presp=pstatus="SKIPPED"
    if lhttp == 200 and lresp == "success" and sid:
        rhttp, _, rraw = req(conn, "/cgi-bin/api.values.get", {"request":"P208","sid":sid}, sh)
        rj=js(rraw); rresp=str(rj.get("response", "")) or "EMPTY"
        body=rj.get("body")
        if isinstance(body,dict) and "P208" in body:
            rpresent="YES"; p208=str(body.get("P208"))
        else:
            rpresent="NO"
        if rhttp == 200 and rresp == "success" and rpresent == "YES":
            phttp, _, praw = req(conn, "/cgi-bin/api.values.post", {"P208":p208,"sid":sid}, sh)
            pj=js(praw); presp=str(pj.get("response", "")) or "EMPTY"
            b=pj.get("body"); pstatus=str(b.get("status", "")) if isinstance(b,dict) else ""
            pstatus=pstatus or "NONE"
    if phttp == 200 and presp == "success": result="WRITE_ACCEPTED"
    elif pstatus == "session-expired": result="WRITE_SESSION_EXPIRED"
    elif lhttp != 200 or lresp != "success" or not sid: result="LOGIN_FAILED"
    elif rresp != "success" or rpresent != "YES": result="READ_FAILED"
    else: result="WRITE_REJECTED_OTHER"
    return {
        "label":label,
        "cookie_available":"YES" if cookies else "NO",
        "cookie_sent":"YES" if (send_cookie and cookies) else "NO",
        "login_http":lhttp,"login_response":lresp,"sid_present":"YES" if sid else "NO",
        "read_http":rhttp,"read_response":rresp,"read_p208_present":rpresent,
        "post_http":phttp,"post_response":presp,"post_status":pstatus,"result":result
    }

cases=[run_case("NO_COOKIE", False), run_case("WITH_COOKIE", True)]
lines=[
    "=== G10-17F GRANDSTREAM BROWSER HEADER WRITE MATRIX ===",
    "db_write=NO","live_code_write=NO","phone_write=SAME-VALUE-P208-ONLY","session_values_logged=NO",
    "host=%s" % HOST,
    "browser_accept_present=YES","browser_accept_language_present=YES","browser_cache_control_present=YES",
    "browser_sec_fetch_dest_present=YES","browser_sec_fetch_mode_present=YES","browser_sec_fetch_site_present=YES",
    "browser_user_agent_present=YES","browser_origin_present=YES","browser_referer_present=YES",
]
for c in cases:
    p=c["label"].lower()
    for k in ["cookie_available","cookie_sent","login_http","login_response","sid_present","read_http","read_response","read_p208_present","post_http","post_response","post_status","result"]:
        lines.append("%s_%s=%s" % (p,k,c[k]))
if any(c["result"] == "WRITE_ACCEPTED" for c in cases):
    diag="BROWSER_HEADER_SHAPE_ACCEPTED"
elif all(c["result"] == "WRITE_SESSION_EXPIRED" for c in cases):
    diag="BROWSER_HEADERS_NOT_SUFFICIENT"
else:
    diag="MIXED_OTHER"
lines += ["diagnostic=%s" % diag, "G10-17F-COMPLETE"]
with open(REPORT,"w",encoding="utf-8") as f: f.write("\n".join(lines)+"\n")
print("\n".join(lines))
