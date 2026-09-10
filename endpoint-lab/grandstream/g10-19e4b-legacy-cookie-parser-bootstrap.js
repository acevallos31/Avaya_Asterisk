#!/usr/bin/env node
'use strict';

const http = require('http');
const fs = require('fs');
const { URLSearchParams } = require('url');

const phoneIp = process.env.PHONE_IP || '192.168.1.167';
const username = process.env.PHONE_USERNAME || 'admin';
const password = process.env.PHONE_PASSWORD || '';
const pbxIp = process.env.PBX_IP || '192.168.1.10';
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19e4b.txt';
if (!password) throw new Error('PHONE_PASSWORD is required');

const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
const jar = new Map();

function absorbLegacySetCookies(res) {
  const raws = [];
  for (let i=0;i<res.rawHeaders.length;i+=2) {
    if (String(res.rawHeaders[i]).toLowerCase()==='set-cookie') raws.push(String(res.rawHeaders[i+1]||''));
  }
  for (const raw of raws) {
    // Firmware may emit malformed comma-separated cookie fragments. Extract only cookie name=value pairs.
    const re = /(?:^|[,;]\s*)([A-Za-z0-9_-]+)=([^,;]*)/g;
    let m;
    while ((m = re.exec(raw)) !== null) {
      const name=m[1], value=m[2];
      if (name && !['Path','Expires','Max-Age','SameSite','Domain'].includes(name)) jar.set(name,value);
    }
  }
}
function cookieHeader(){ return [...jar.entries()].map(([k,v])=>`${k}=${v}`).join('; '); }
function post(path, body) {
  return new Promise((resolve,reject)=>{
    const data=new URLSearchParams(body).toString();
    const headers={
      'Accept':'*/*','Accept-Encoding':'gzip, deflate','Accept-Language':'es-ES,es;q=0.9',
      'Cache-Control':'max-age=0','Connection':'keep-alive',
      'Content-Type':'application/x-www-form-urlencoded','Content-Length':Buffer.byteLength(data),
      'Host':phoneIp,'Origin':`http://${phoneIp}`,'Referer':`http://${phoneIp}/`,
      'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36'
    };
    const ck=cookieHeader(); if(ck) headers.Cookie=ck;
    const req=http.request({host:phoneIp,port:80,path,method:'POST',headers,agent,insecureHTTPParser:true},res=>{
      let text=''; res.setEncoding('utf8'); absorbLegacySetCookies(res);
      res.on('data',c=>text+=c); res.on('end',()=>resolve({status:res.statusCode||0,text}));
    });
    req.on('error',reject); req.end(data);
  });
}
function parse(r){try{return JSON.parse(r.text)}catch(_){return null}}
function b(j){return j&&j.body&&typeof j.body==='object'?j.body:{}}

(async()=>{
  const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
  log('scope','CONTROLLED_PHONE_BOOTSTRAP'); log('transport','LAN_HTTP_LEGACY_COOKIE_PARSE');
  log('db_write','NO'); log('pbx_live_code_write','NO'); log('factory_reset','NO');

  const login=await post('/cgi-bin/dologin',{username,password});
  const lj=parse(login); const sid=lj&&lj.body&&lj.body.sid?String(lj.body.sid):'';
  log('login',login.status===200&&lj&&lj.response==='success'&&sid?'SUCCESS':'FAILED');
  log('cookie_names',[...jar.keys()].sort().join(',')||'NONE');
  log('session_identity_cookie_present',jar.has('session-identity')?'YES':'NO');
  log('session_role_cookie_present',jar.has('session-role')?'YES':'NO');
  if(!sid){log('phone_write','NO');log('diagnostic','LOGIN_FAILED');return finish();}

  const pre=await post('/cgi-bin/api.values.get',{request:'P212:P237',sid});
  const pj=parse(pre),po=b(pj); const preOk=pre.status===200&&pj&&pj.response==='success';
  log('pre_read',preOk?'SUCCESS':'FAILED');
  if(!preOk){log('phone_write','NO');log('diagnostic','PRE_READ_FAILED');return finish();}

  if(String(po.P212)==='0'&&String(po.P237)===pbxIp){
    log('phone_write','NO_ALREADY_CONFIGURED');
  } else {
    const wr=await post('/cgi-bin/api.values.post',{P212:'0',P237:pbxIp,sid});
    const wj=parse(wr); const st=wj&&wj.body&&wj.body.status?String(wj.body.status):'EMPTY';
    log('phone_write','YES_CONTROLLED_P212_P237'); log('bootstrap_post_http',wr.status);
    log('bootstrap_post_response',wj&&wj.response?String(wj.response):'EMPTY'); log('bootstrap_post_status',st);
  }

  const ver=await post('/cgi-bin/api.values.get',{request:'P212:P237',sid});
  const vj=parse(ver),vo=b(vj); const a=String(vo.P212)==='0', c=String(vo.P237)===pbxIp;
  log('verify_read',ver.status===200&&vj&&vj.response==='success'?'SUCCESS':'FAILED');
  log('p212_target_match',a?'YES':'NO'); log('p237_target_match',c?'YES':'NO');
  log('diagnostic',a&&c?'PHONE_TFTP_BOOTSTRAP_READY':'LEGACY_COOKIE_PARSE_STILL_NOT_ACCEPTED');
  log('next_activity',a&&c?'G10-19F_PHONE_CFG_REQUEST_PROOF':'G10-19E4C_SESSION_IDENTITY_SOURCE');
  finish();

  function finish(){log('G10-19E4B-COMPLETE','YES');fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});console.log(lines.join('\n'));agent.destroy();}
})().catch(err=>{const t=['scope=CONTROLLED_PHONE_BOOTSTRAP','phone_write=UNKNOWN','diagnostic=G10-19E4B_RUNTIME_ERROR','error_class='+(err&&err.code?err.code:'NODE_ERROR'),'G10-19E4B-COMPLETE=YES'].join('\n')+'\n';fs.writeFileSync(reportPath,t,{mode:0o600});console.log(t.trim());process.exitCode=1;});
