#!/usr/bin/env python3
"""G10-17E: controlled GXP1625 host-context write matrix.

LAB only. Tests two independently authenticated sessions against the physical
phone while connecting directly to its LAN IP:
A) IP web context
B) tunnel-host web context
Each case reads P208 first and only posts the exact same current value back.
No secret/session values are printed.
"""
import http.client, json, os, sys, urllib.parse

PHONE_IP = "192.168.1.167"
TUNNEL_HOST = "phone1.nocpbx.com"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17e-host-context-write-matrix.txt"
if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")

def req(conn, path, form, headers):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=headers)
    r = conn.getresponse(); raw = r.read()
    return r.status, r.getheaders(), raw

def js(raw):
    try: return json.loads(raw.decode("utf-8"))
    except Exception: return {}

def run_case(label, host, scheme):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": host,
        "Origin": "%s://%s" % (scheme, host),
        "Referer": "%s://%s/" % (scheme, host),
    }
    conn = http.client.HTTPConnection(PHONE_IP, timeout=10)
    lhttp, lhdrs, lraw = req(conn, "/cgi-bin/dologin", {"username": USERNAME, "password": PASSWORD}, dict(headers))
    lj = js(lraw); lresp = str(lj.get("response", ""))
    sid = ""
    if isinstance(lj.get("body"), dict): sid = str(lj["body"].get("sid") or "")
    cookies = []
    for n,v in lhdrs:
        if n.lower() == "set-cookie":
            pair = v.split(";",1)[0].strip()
            if pair and "=" in pair: cookies.append(pair)
    sh = dict(headers)
    if cookies: sh["Cookie"] = "; ".join(cookies)
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
        "label":label,"host":host,"scheme":scheme,"login_http":lhttp,"login_response":lresp or "EMPTY",
        "sid_present":"YES" if sid else "NO","cookie_present":"YES" if cookies else "NO","cookie_count":len(cookies),
        "read_http":rhttp,"read_response":rresp,"read_p208_present":rpresent,
        "post_http":phttp,"post_response":presp,"post_status":pstatus,"result":result
    }

cases=[run_case("IP_CONTEXT", PHONE_IP, "http"), run_case("TUNNEL_HOST_CONTEXT", TUNNEL_HOST, "https")]
lines=["=== G10-17E GRANDSTREAM HOST CONTEXT WRITE MATRIX ===","db_write=NO","live_code_write=NO","phone_write=SAME-VALUE-P208-ONLY","session_values_logged=NO"]
for c in cases:
    p=c["label"].lower()
    for k in ["host","scheme","login_http","login_response","sid_present","cookie_present","cookie_count","read_http","read_response","read_p208_present","post_http","post_response","post_status","result"]:
        lines.append("%s_%s=%s" % (p,k,c[k]))
if cases[0]["result"] == "WRITE_SESSION_EXPIRED" and cases[1]["result"] == "WRITE_ACCEPTED":
    diag="TUNNEL_HOST_CONTEXT_REQUIRED_FOR_WRITE"
elif cases[0]["result"] == "WRITE_ACCEPTED" and cases[1]["result"] == "WRITE_ACCEPTED":
    diag="BOTH_CONTEXTS_ACCEPTED"
elif cases[0]["result"] == "WRITE_SESSION_EXPIRED" and cases[1]["result"] == "WRITE_SESSION_EXPIRED":
    diag="HOST_CONTEXT_NOT_SUFFICIENT"
else:
    diag="MIXED_OTHER"
lines += ["diagnostic=%s" % diag, "G10-17E-COMPLETE"]
with open(REPORT,"w",encoding="utf-8") as f: f.write("\n".join(lines)+"\n")
print("\n".join(lines))
