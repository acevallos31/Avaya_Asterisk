#!/usr/bin/env python3
"""G10-17K: controlled browser-sequence matrix for Grandstream GXP1625.

LAB only. Tests only sequences built from endpoints already observed in the phone UI:
- GET /
- POST /cgi-bin/dologin
- POST /cgi-bin/api.values.get
- POST /cgi-bin/api-get_phone_status
- POST /cgi-bin/api.values.post

Every write re-posts the current P208 value read immediately beforehand.
No password, SID or cookie value is printed.
"""
import http.client, json, os, sys, time, urllib.parse

PHONE_IP = "192.168.1.167"
HOST = "192.168.1.167"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17k-browser-sequence-matrix.txt"
if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"

def headers():
    return {
        "Host": HOST,
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://%s" % HOST,
        "Referer": "http://%s/" % HOST,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": UA,
    }

def post(conn, path, form, hdr):
    body = urllib.parse.urlencode(form)
    conn.request("POST", path, body=body, headers=hdr)
    r = conn.getresponse(); raw = r.read()
    return r.status, r.getheaders(), raw

def get(conn, path, hdr):
    gh = dict(hdr); gh.pop("Content-Type", None); gh.pop("Origin", None)
    conn.request("GET", path, headers=gh)
    r = conn.getresponse(); raw = r.read()
    return r.status, r.getheaders(), raw

def js(raw):
    try: return json.loads(raw.decode("utf-8"))
    except Exception: return {}

def cookie_pairs(hdrs):
    out=[]
    for n,v in hdrs:
        if n.lower()=="set-cookie":
            p=v.split(";",1)[0].strip()
            if p and "=" in p: out.append(p)
    return out

def merge_cookies(store, hdrs):
    pairs=cookie_pairs(hdrs)
    if not pairs: return store
    merged={}
    for p in store+pairs:
        k=p.split("=",1)[0]; merged[k]=p
    return list(merged.values())

def run_case(idx, preload_root, status_count, read_request, delay_ms):
    h=headers(); conn=http.client.HTTPConnection(PHONE_IP, timeout=10); cookies=[]
    if preload_root:
        try:
            _, rh, _ = get(conn, "/", h); cookies=merge_cookies(cookies, rh)
        except Exception:
            pass

    lhttp, lhdrs, lraw=post(conn,"/cgi-bin/dologin",{"username":USERNAME,"password":PASSWORD},dict(h))
    cookies=merge_cookies(cookies, lhdrs)
    lj=js(lraw); lresp=str(lj.get("response", "")) or "EMPTY"; sid=""
    if isinstance(lj.get("body"),dict): sid=str(lj["body"].get("sid") or "")
    sh=dict(h)
    if cookies: sh["Cookie"]="; ".join(cookies)
    if not (lhttp==200 and lresp=="success" and sid):
        return "LOGIN_FAILED", "login"

    for _ in range(status_count):
        try:
            _, ah, _=post(conn,"/cgi-bin/api-get_phone_status",{"sid":sid},sh)
            cookies=merge_cookies(cookies, ah)
            if cookies: sh["Cookie"]="; ".join(cookies)
        except Exception:
            return "PRESEQ_FAILED", "status"
        if delay_ms: time.sleep(delay_ms/1000.0)

    rhttp, rh, rraw=post(conn,"/cgi-bin/api.values.get",{"request":read_request,"sid":sid},sh)
    cookies=merge_cookies(cookies, rh)
    if cookies: sh["Cookie"]="; ".join(cookies)
    rj=js(rraw); rresp=str(rj.get("response", "")) or "EMPTY"; body=rj.get("body")
    p208=""
    if isinstance(body,dict) and "P208" in body: p208=str(body.get("P208"))
    if not (rhttp==200 and rresp=="success" and p208!=""):
        return "READ_FAILED", "read"
    if delay_ms: time.sleep(delay_ms/1000.0)

    phttp, ph, praw=post(conn,"/cgi-bin/api.values.post",{"P208":p208,"sid":sid},sh)
    pj=js(praw); presp=str(pj.get("response", "")) or "EMPTY"; b=pj.get("body")
    pstatus=str(b.get("status", "")) if isinstance(b,dict) else ""; pstatus=pstatus or "NONE"
    if phttp==200 and presp=="success": return "WRITE_ACCEPTED", pstatus
    if pstatus=="session-expired": return "WRITE_SESSION_EXPIRED", pstatus
    return "WRITE_REJECTED_OTHER", pstatus

cases=[]; n=0; accepted="NONE"
for preload in (False, True):
  for status_count in (0,1,2):
    for read_request in ("P208","P35:P208"):
      for delay_ms in (0,200):
        n+=1
        result, detail=run_case(n,preload,status_count,read_request,delay_ms)
        label="preload=%s|status_count=%d|read=%s|delay_ms=%d" % ("YES" if preload else "NO",status_count,read_request,delay_ms)
        cases.append("case_%03d=%s|%s|detail=%s" % (n,result,label,detail))
        if result=="WRITE_ACCEPTED":
            accepted="case_%03d|%s" % (n,label)
            break
      if accepted!="NONE": break
    if accepted!="NONE": break
  if accepted!="NONE": break

lines=[
 "=== G10-17K GRANDSTREAM BROWSER SEQUENCE MATRIX ===",
 "db_write=NO","live_code_write=NO","phone_write=SAME-VALUE-P208-ONLY","session_values_logged=NO",
 "sequence_source=OBSERVED_UI_ENDPOINTS_ONLY",
 "case_count=%d" % n,
] + cases + [
 "accepted_case=%s" % accepted,
 "diagnostic=%s" % ("BROWSER_SEQUENCE_ACCEPTED" if accepted!="NONE" else "BROWSER_SEQUENCE_NOT_SUFFICIENT"),
 "G10-17K-COMPLETE"
]
with open(REPORT,"w",encoding="utf-8") as f: f.write("\n".join(lines)+"\n")
print("\n".join(lines))
