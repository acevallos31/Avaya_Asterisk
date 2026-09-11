#!/usr/bin/env python3
import http.client, json, os, urllib.parse

ip=os.environ.get('PHONE_IP','192.168.1.169')
user=os.environ.get('PHONE_USERNAME','admin')
password=os.environ.get('PHONE_PASSWORD','')
pbx=os.environ.get('PBX_IP','192.168.1.10')
report=os.environ.get('REPORT_PATH','/tmp/test57.txt')
if not password: raise SystemExit('PHONE_PASSWORD missing')
lines=[]
def log(k,v): lines.append('%s=%s'%(k,v)); print(lines[-1])
def call(conn,path,data):
    body=urllib.parse.urlencode(data)
    conn.request('POST',path,body=body,headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'*/*','Host':ip,'Referer':'http://%s/'%ip})
    r=conn.getresponse(); raw=r.read().decode('utf-8','replace')
    try: obj=json.loads(raw)
    except Exception: obj={}
    return r.status,obj
log('scope','TEST57_GXP1630_CONTROLLED_BOOTSTRAP')
log('target_ip',ip); log('phone_write','PENDING')
conn=http.client.HTTPConnection(ip,80,timeout=6)
status,obj=call(conn,'/cgi-bin/dologin',{'username':user,'password':password})
sid=(obj.get('body') or {}).get('sid','') if isinstance(obj,dict) else ''
log('login','SUCCESS' if status==200 and obj.get('response')=='success' and sid else 'FAILED')
if not sid: raise SystemExit('login failed')
status,obj=call(conn,'/cgi-bin/api.values.get',{'request':'P212:P237','sid':sid})
b=obj.get('body') or {}
log('pre_read','SUCCESS' if status==200 and obj.get('response')=='success' else 'FAILED')
already=str(b.get('P212',''))=='0' and str(b.get('P237',''))==pbx
if not already:
    status,obj=call(conn,'/cgi-bin/api.values.post',{'P212':'0','P237':pbx,'sid':sid})
    log('write_http',status); log('write_response',obj.get('response','EMPTY'))
    log('phone_write','YES_CONTROLLED_P212_P237')
else: log('phone_write','NO_ALREADY_CONFIGURED')
status,obj=call(conn,'/cgi-bin/api.values.get',{'request':'P212:P237','sid':sid})
b=obj.get('body') or {}
ok=status==200 and obj.get('response')=='success' and str(b.get('P212',''))=='0' and str(b.get('P237',''))==pbx
log('p212_target_match','YES' if str(b.get('P212',''))=='0' else 'NO')
log('p237_target_match','YES' if str(b.get('P237',''))==pbx else 'NO')
log('diagnostic','PHONE_TFTP_BOOTSTRAP_READY' if ok else 'PHONE_TFTP_BOOTSTRAP_NOT_APPLIED')
log('TEST57-GXP1630-BOOTSTRAP','PASS' if ok else 'FAIL')
open(report,'w',encoding='utf-8').write('\n'.join(lines)+'\n')
if not ok: raise SystemExit(1)
