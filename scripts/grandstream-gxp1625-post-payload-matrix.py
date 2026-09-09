#!/usr/bin/env python3
"""G10-17I: controlled GXP1625 POST payload matrix.

LAB only. Authenticates to the phone, reads current P208, then performs four
same-value api.values.post variants that differ only in form-body construction.
No DB/live-code writes. No password, SID, cookie or raw response values logged.
"""
import http.client, json, os, sys, urllib.parse

PHONE_IP = "192.168.1.167"
HOST = "phone1.nocpbx.com"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17i-post-payload-matrix.txt"
if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")

BASE_HEADERS = {
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
}

def post_raw(conn, path, body, headers):
    h = dict(headers)
    h["Content-Length"] = str(len(body.encode("utf-8")))
    conn.request("POST", path, body=body, headers=h)
    r = conn.getresponse(); raw = r.read()
    return r.status, r.getheaders(), raw

def form_body(pairs):
    return urllib.parse.urlencode(pairs)

def js(raw):
    try: return json.loads(raw.decode("utf-8"))
    except Exception: return {}

def cookies_from(headers):
    out=[]
    for n,v in headers:
        if n.lower()=="set-cookie":
            pair=v.split(";",1)[0].strip()
            if pair and "=" in pair: out.append(pair)
    return out

def authenticate_and_read():
    conn=http.client.HTTPConnection(PHONE_IP, timeout=10)
    lbody=form_body([("username",USERNAME),("password",PASSWORD)])
    lhttp, lhdrs, lraw=post_raw(conn,"/cgi-bin/dologin",lbody,BASE_HEADERS)
    lj=js(lraw); lresp=str(lj.get("response", "")) or "EMPTY"
    sid=""
    if isinstance(lj.get("body"),dict): sid=str(lj["body"].get("sid") or "")
    cookies=cookies_from(lhdrs)
    sh=dict(BASE_HEADERS)
    if cookies: sh["Cookie"]="; ".join(cookies)
    rhttp=rresp="SKIPPED"; present="NO"; p208=""
    if lhttp==200 and lresp=="success" and sid:
        rbody=form_body([("request","P208"),("sid",sid)])
        rhttp, _, rraw=post_raw(conn,"/cgi-bin/api.values.get",rbody,sh)
        rj=js(rraw); rresp=str(rj.get("response", "")) or "EMPTY"
        body=rj.get("body")
        if isinstance(body,dict) and "P208" in body:
            present="YES"; p208=str(body.get("P208"))
    return conn, sh, lhttp, lresp, bool(sid), sid, rhttp, rresp, present, p208

def run_variant(label, builder):
    conn, headers, lhttp, lresp, sid_present, sid, rhttp, rresp, present, p208 = authenticate_and_read()
    phttp=presp=pstatus="SKIPPED"; body_len="SKIPPED"
    if lhttp==200 and lresp=="success" and sid_present and rhttp==200 and rresp=="success" and present=="YES":
        body=builder(p208,sid)
        body_len=len(body.encode("utf-8"))
        phttp, _, praw=post_raw(conn,"/cgi-bin/api.values.post",body,headers)
        pj=js(praw); presp=str(pj.get("response", "")) or "EMPTY"
        b=pj.get("body"); pstatus=str(b.get("status", "")) if isinstance(b,dict) else ""
        pstatus=pstatus or "NONE"
    if phttp==200 and presp=="success": result="WRITE_ACCEPTED"
    elif pstatus=="session-expired": result="WRITE_SESSION_EXPIRED"
    elif lhttp!=200 or lresp!="success" or not sid_present: result="LOGIN_FAILED"
    elif rhttp!=200 or rresp!="success" or present!="YES": result="READ_FAILED"
    else: result="WRITE_REJECTED_OTHER"
    try: conn.close()
    except Exception: pass
    return {"label":label,"body_len":body_len,"post_http":phttp,"post_response":presp,"post_status":pstatus,"result":result}

variants=[
    ("P208_THEN_SID", lambda p,s: form_body([("P208",p),("sid",s)])),
    ("SID_THEN_P208", lambda p,s: form_body([("sid",s),("P208",p)])),
    ("P208_SID_EMPTY_UNDERSCORE", lambda p,s: form_body([("P208",p),("sid",s),("_","")])),
    ("P208_SID_RAW_FORM", lambda p,s: "P208=%s&sid=%s" % (urllib.parse.quote_plus(p), urllib.parse.quote_plus(s))),
]

results=[run_variant(label,builder) for label,builder in variants]
lines=["=== G10-17I GRANDSTREAM POST PAYLOAD MATRIX ===","db_write=NO","live_code_write=NO","phone_write=SAME-VALUE-P208-ONLY","session_values_logged=NO"]
for r in results:
    p=r["label"].lower()
    for k in ["body_len","post_http","post_response","post_status","result"]:
        lines.append("%s_%s=%s" % (p,k,r[k]))
accepted=[r["label"] for r in results if r["result"]=="WRITE_ACCEPTED"]
if accepted:
    diag="PAYLOAD_VARIANT_ACCEPTED:"+",".join(accepted)
elif all(r["result"]=="WRITE_SESSION_EXPIRED" for r in results):
    diag="PAYLOAD_SHAPE_NOT_SUFFICIENT"
else:
    diag="MIXED_OTHER"
lines += ["diagnostic=%s" % diag,"G10-17I-COMPLETE"]
with open(REPORT,"w",encoding="utf-8") as f: f.write("\n".join(lines)+"\n")
print("\n".join(lines))
