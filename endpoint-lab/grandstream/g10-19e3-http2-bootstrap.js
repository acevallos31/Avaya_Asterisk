#!/usr/bin/env node
'use strict';

const http2 = require('http2');
const fs = require('fs');
const { URLSearchParams } = require('url');

const origin = process.env.PHONE_TUNNEL_ORIGIN || 'https://phone1.nocpbx.com';
const username = process.env.PHONE_USERNAME || 'admin';
const password = process.env.PHONE_PASSWORD || '';
const pbxIp = process.env.PBX_IP || '192.168.1.10';
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19e3-http2-bootstrap.txt';
if (!password) throw new Error('PHONE_PASSWORD is required');

let cookies = [];
function absorbCookies(headers) {
  const raw = headers['set-cookie'];
  const set = Array.isArray(raw) ? raw : (raw ? [raw] : []);
  for (const c of set) {
    const pair = String(c).split(';',1)[0];
    const name = pair.split('=',1)[0];
    cookies = cookies.filter(x => !x.startsWith(name+'='));
    cookies.push(pair);
  }
}

function post(session, path, body) {
  return new Promise((resolve, reject) => {
    const data = new URLSearchParams(body).toString();
    const u = new URL(origin);
    const headers = {
      ':method':'POST', ':path':path, ':scheme':'https', ':authority':u.host,
      'accept':'*/*',
      'content-type':'application/x-www-form-urlencoded',
      'origin':origin,
      'referer':origin+'/',
      'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36',
      'content-length': Buffer.byteLength(data)
    };
    if (cookies.length) headers['cookie'] = cookies.join('; ');
    const req = session.request(headers);
    let status = 0, rh = {}, text='';
    req.setEncoding('utf8');
    req.on('response', h => { rh=h; status=Number(h[':status']||0); absorbCookies(h); });
    req.on('data', c => text += c);
    req.on('end', () => resolve({status, headers:rh, text}));
    req.on('error', reject);
    req.end(data);
  });
}
function parse(r){ try{return JSON.parse(r.text)}catch(_){return null} }
function body(j){ return j && j.body && typeof j.body==='object' ? j.body : {}; }

(async()=>{
  const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
  log('scope','CONTROLLED_PHONE_BOOTSTRAP');
  log('transport','HTTPS_HTTP2_SINGLE_SESSION');
  log('db_write','NO'); log('pbx_live_code_write','NO'); log('factory_reset','NO');
  const session = http2.connect(origin);
  let sessionClosed=false;
  session.on('close',()=>{sessionClosed=true;});
  session.on('error',()=>{});

  const login=await post(session,'/cgi-bin/dologin',{username,password});
  const lj=parse(login); const sid=lj&&lj.body&&lj.body.sid?String(lj.body.sid):'';
  log('login',login.status===200&&lj&&lj.response==='success'&&sid?'SUCCESS':'FAILED');
  log('login_http',login.status); log('session_alive_after_login',!sessionClosed&&!session.closed?'YES':'NO');
  if(!sid){ log('phone_write','NO'); log('diagnostic','HTTP2_BOOTSTRAP_LOGIN_FAILED'); finish(); return; }

  const pre=await post(session,'/cgi-bin/api.values.get',{request:'P212:P237',sid});
  const pj=parse(pre), po=body(pj);
  const preOk=pre.status===200&&pj&&pj.response==='success'&&Object.prototype.hasOwnProperty.call(po,'P212')&&Object.prototype.hasOwnProperty.call(po,'P237');
  log('pre_read',preOk?'SUCCESS':'FAILED'); log('pre_read_http',pre.status);
  log('session_alive_after_read',!sessionClosed&&!session.closed?'YES':'NO');
  if(!preOk){ log('phone_write','NO'); log('diagnostic','HTTP2_BOOTSTRAP_PRE_READ_FAILED'); finish(); return; }

  const already=String(po.P212)==='0'&&String(po.P237)===pbxIp;
  if(already){
    log('phone_write','NO_ALREADY_CONFIGURED'); log('bootstrap_post','SKIPPED');
  } else {
    const wr=await post(session,'/cgi-bin/api.values.post',{P212:'0',P237:pbxIp,sid});
    const wj=parse(wr); const st=wj&&wj.body&&wj.body.status?String(wj.body.status):'EMPTY';
    log('phone_write','YES_CONTROLLED_P212_P237'); log('bootstrap_post_http',wr.status);
    log('bootstrap_post_response',wj&&wj.response?String(wj.response):'EMPTY'); log('bootstrap_post_status',st);
    log('session_alive_after_write',!sessionClosed&&!session.closed?'YES':'NO');
  }

  const ver=await post(session,'/cgi-bin/api.values.get',{request:'P212:P237',sid});
  const vj=parse(ver), vo=body(vj);
  const ok=ver.status===200&&vj&&vj.response==='success'&&String(vo.P212)==='0'&&String(vo.P237)===pbxIp;
  log('verify_read',ver.status===200&&vj&&vj.response==='success'?'SUCCESS':'FAILED');
  log('p212_target_match',String(vo.P212)==='0'?'YES':'NO');
  log('p237_target_match',String(vo.P237)===pbxIp?'YES':'NO');
  log('same_http2_session','YES');
  log('diagnostic',ok?'PHONE_TFTP_BOOTSTRAP_READY':'HTTP2_WRITE_STILL_NOT_ACCEPTED');
  log('next_activity',ok?'G10-19F_PHONE_CFG_REQUEST_PROOF':'G10-19E4_BROWSER_HAR_SANITIZED_COMPARE');
  finish();

  function finish(){
    log('G10-19E3-COMPLETE','YES');
    fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});
    console.log(lines.join('\n'));
    try{session.close();}catch(_){ }
  }
})().catch(err=>{
  const txt=['scope=CONTROLLED_PHONE_BOOTSTRAP','phone_write=UNKNOWN','diagnostic=G10-19E3_RUNTIME_ERROR','error_class='+(err&&err.code?err.code:'NODE_ERROR'),'G10-19E3-COMPLETE=YES'].join('\n')+'\n';
  fs.writeFileSync(reportPath,txt,{mode:0o600}); console.log(txt.trim()); process.exitCode=1;
});
