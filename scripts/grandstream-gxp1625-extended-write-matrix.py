#!/usr/bin/env python3
"""G10-17J: extended controlled write matrix for Grandstream GXP1625.
LAB only. Every write posts the exact current P208 value. No secrets/session values printed.
"""
import http.client, json, os, sys, urllib.parse

PHONE_IP = "192.168.1.167"
HOST = "phone1.nocpbx.com"
USERNAME = os.environ.get("GRANDSTREAM_HTTP_USERNAME", "admin")
PASSWORD = os.environ.get("GRANDSTREAM_HTTP_PASSWORD", "")
REPORT = sys.argv[1] if len(sys.argv) > 1 else "g10-17j-extended-write-matrix.txt"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
if not PASSWORD:
    raise SystemExit("ERROR: GRANDSTREAM_HTTP_PASSWORD no definido")

def js(raw):
    try: return json.loads(raw.decode("utf-8"))
    except Exception: return {}

def cookies_from(headers):
    out=[]
    for n,v in headers:
        if n.lower()=="set-cookie":
            p=v.split(";",1)[0].strip()
            if p and "=" in p: out.append(p)
    return out

def headers(profile, cookie=None):
    h={"Content-Type":"application/x-www-form-urlencoded"}
    if profile in ("ip_basic","ip_browser"):
        h["Host"]=PHONE_IP; h["Referer"]="http://%s/" % PHONE_IP
    else:
        h["Host"]=HOST; h["Referer"]="https://%s/" % HOST; h["Origin"]="https://%s" % HOST
    if profile in ("ip_browser","tunnel_browser"):
        h.update({"Accept":"*/*","Accept-Language":"es-ES,es;q=0.9","Cache-Control":"max-age=0",
                  "Sec-Fetch-Dest":"empty","Sec-Fetch-Mode":"cors","Sec-Fetch-Site":"same-origin","User-Agent":UA})
    if cookie: h["Cookie"]="; ".join(cookie)
    return h

def request(conn,path,body,h):
    conn.request("POST",path,body=body,headers=h)
    r=conn.getresponse(); raw=r.read()
    return r.status,r.getheaders(),raw

def login(profile, persistent=True):
    conn=http.client.HTTPConnection(PHONE_IP,timeout=10)
    body=urllib.parse.urlencode([("username",USERNAME),("password",PASSWORD)])
    st,hs,raw=request(conn,"/cgi-bin/dologin",body,headers(profile))
    j=js(raw); sid=""
    if isinstance(j.get("body"),dict): sid=str(j["body"].get("sid") or "")
    if not persistent: conn.close(); conn=http.client.HTTPConnection(PHONE_IP,timeout=10)
    return conn,st,str(j.get("response","") or "EMPTY"),sid,cookies_from(hs)

def read_p208(conn,profile,sid,cookie,preseq):
    h=headers(profile,cookie)
    if preseq=="status":
        request(conn,"/cgi-bin/api-get_phone_status",urllib.parse.urlencode([("sid",sid)]),h)
    elif preseq=="double_read":
        request(conn,"/cgi-bin/api.values.get",urllib.parse.urlencode([("request","P35:P208"),("sid",sid)]),h)
    body=urllib.parse.urlencode([("request","P208"),("sid",sid)])
    st,hs,raw=request(conn,"/cgi-bin/api.values.get",body,h)
    j=js(raw); p=""; present=False
    if isinstance(j.get("body"),dict) and "P208" in j["body"]:
        p=str(j["body"].get("P208")); present=True
    return st,str(j.get("response","") or "EMPTY"),p,present,cookies_from(hs)

def make_body(kind,p208,sid):
    if kind=="p208_sid": return urllib.parse.urlencode([("P208",p208),("sid",sid)])
    if kind=="sid_p208": return urllib.parse.urlencode([("sid",sid),("P208",p208)])
    if kind=="p208_sid_empty": return urllib.parse.urlencode([("P208",p208),("sid",sid),("_","")])
    if kind=="p208_sid_space": return "P208=%s&sid=%s" % (urllib.parse.quote_plus(p208), urllib.parse.quote_plus(sid))
    if kind=="sid_p208_space": return "sid=%s&P208=%s" % (urllib.parse.quote_plus(sid), urllib.parse.quote_plus(p208))
    return urllib.parse.urlencode([("P208",p208),("sid",sid)])

cases=[]
profiles=["ip_basic","ip_browser","tunnel_browser"]
bodykinds=["p208_sid","sid_p208","p208_sid_empty","p208_sid_space","sid_p208_space"]
preseqs=["none","status","double_read"]
for persistent in (True,False):
  for profile in profiles:
    for send_cookie in (False,True):
      for preseq in preseqs:
        for bodykind in bodykinds:
          cases.append((persistent,profile,send_cookie,preseq,bodykind))

lines=["=== G10-17J GRANDSTREAM EXTENDED WRITE MATRIX ===","db_write=NO","live_code_write=NO","phone_write=SAME-VALUE-P208-ONLY","session_values_logged=NO","case_count=%d"%len(cases)]
accepted=None
for idx,(persistent,profile,send_cookie,preseq,bodykind) in enumerate(cases,1):
    conn,lh,lr,sid,lc=login(profile,persistent)
    result="LOGIN_FAILED"; ph=pr=ps="SKIPPED"; body_len="NA"
    if lh==200 and lr=="success" and sid:
        cookie=lc if send_cookie and lc else None
        rh,rr,p208,present,rc=read_p208(conn,profile,sid,cookie,preseq)
        if send_cookie and rc: cookie=rc
        if rh==200 and rr=="success" and present:
            b=make_body(bodykind,p208,sid); body_len=len(b.encode("utf-8"))
            ph,_,raw=request(conn,"/cgi-bin/api.values.post",b,headers(profile,cookie))
            pj=js(raw); pr=str(pj.get("response","") or "EMPTY")
            pb=pj.get("body"); ps=str(pb.get("status","") if isinstance(pb,dict) else "") or "NONE"
            if ph==200 and pr=="success": result="WRITE_ACCEPTED"
            elif ps=="session-expired": result="WRITE_SESSION_EXPIRED"
            else: result="WRITE_REJECTED_OTHER"
        else: result="READ_FAILED"
    try: conn.close()
    except Exception: pass
    lines.append("case_%03d=%s|profile=%s|persistent=%s|cookie=%s|preseq=%s|body=%s|len=%s|post_http=%s|post_response=%s|post_status=%s" % (
        idx,result,profile,"YES" if persistent else "NO","YES" if send_cookie else "NO",preseq,bodykind,body_len,ph,pr,ps))
    if result=="WRITE_ACCEPTED":
        accepted=idx; break

if accepted:
    lines.append("accepted_case=%03d"%accepted); lines.append("diagnostic=EXTENDED_MATRIX_WRITE_ACCEPTED")
else:
    lines.append("accepted_case=NONE"); lines.append("diagnostic=EXTENDED_MATRIX_NO_ACCEPTED_WRITE")
lines.append("G10-17J-COMPLETE")
with open(REPORT,"w",encoding="utf-8") as f: f.write("\n".join(lines)+"\n")
print("\n".join(lines))
