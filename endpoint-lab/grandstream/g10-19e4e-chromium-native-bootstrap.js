#!/usr/bin/env node
'use strict';

const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const phoneBase = process.env.PHONE_BASE || 'http://192.168.1.167';
const username = process.env.PHONE_USERNAME || 'admin';
const password = process.env.PHONE_PASSWORD || '';
const pbxIp = process.env.PBX_IP || '192.168.1.10';
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19e4e.txt';
if (!password) throw new Error('PHONE_PASSWORD is required');

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'gxp1625-bootstrap-'));
const chrome = spawn('/usr/bin/chromium', [
  '--headless=new','--disable-gpu','--no-sandbox',
  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9223',
  `--user-data-dir=${profile}`,'about:blank'
], {stdio:'ignore'});

const lines=[];
const log=(k,v)=>lines.push(`${k}=${v}`);
log('scope','CONTROLLED_CHROMIUM_NATIVE_PROVISIONING_BOOTSTRAP');
log('phone_write','P212_P237_ONLY');
log('db_write','NO');
log('pbx_live_code_write','NO');
log('factory_reset','NO');
log('secrets_logged','NO');

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function getJson(url){ return new Promise((resolve,reject)=>{ http.get(url,res=>{ let d=''; res.on('data',c=>d+=c); res.on('end',()=>{ try{resolve(JSON.parse(d))}catch(e){reject(e)} }); }).on('error',reject); }); }

(async()=>{
  let target;
  for(let i=0;i<30;i++){
    try{ const list=await getJson('http://127.0.0.1:9223/json/list'); target=list.find(x=>x.type==='page'); if(target) break; }catch(_){ }
    await sleep(200);
  }
  if(!target || !target.webSocketDebuggerUrl) throw new Error('CDP_TARGET_NOT_FOUND');
  const ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let seq=0; const pending=new Map();
  function cmd(method,params={}){ return new Promise((resolve,reject)=>{ const id=++seq; pending.set(id,{resolve,reject}); ws.send(JSON.stringify({id,method,params})); setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(new Error('CDP_TIMEOUT_'+method));}},8000); }); }
  let loginRequestId=null;
  ws.onmessage=(ev)=>{
    let m; try{m=JSON.parse(ev.data)}catch(_){return}
    if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);return;}
    if(m.method==='Network.responseReceived'){
      const p=m.params||{}; const r=p.response||{};
      try{ if(new URL(r.url).pathname==='/cgi-bin/dologin' && r.status===200) loginRequestId=p.requestId; }catch(_){ }
    }
  };
  await cmd('Network.enable'); await cmd('Page.enable'); await cmd('Runtime.enable');
  await cmd('Page.navigate',{url:phoneBase+'/'}); await sleep(2500);

  let loginUi='NOT_FOUND';
  for(let i=0;i<12;i++){
    const r=await cmd('Runtime.evaluate',{expression:`(()=>{const p=document.querySelector('input[type=password]');if(!p)return 'NO_PASSWORD_INPUT';const u=document.querySelector('input[type=text],input[name*=user i],input[id*=user i]');if(u){u.focus();u.value=${JSON.stringify(username)};u.dispatchEvent(new Event('input',{bubbles:true}));u.dispatchEvent(new Event('change',{bubbles:true}));}p.focus();p.value=${JSON.stringify(password)};p.dispatchEvent(new Event('input',{bubbles:true}));p.dispatchEvent(new Event('change',{bubbles:true}));const f=p.closest('form');const b=(f&&f.querySelector('button,input[type=submit]'))||[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/login|log in|sign in|entrar/i.test(x.innerText||x.value||''));if(b){b.click();return 'CLICKED';}if(f){if(f.requestSubmit)f.requestSubmit();else f.submit();return 'FORM_SUBMITTED';}return 'NO_SUBMIT_CONTROL';})()`,returnByValue:true});
    loginUi=r&&r.result&&r.result.value?r.result.value:'UNKNOWN';
    if(loginUi==='CLICKED'||loginUi==='FORM_SUBMITTED') break;
    await sleep(500);
  }
  log('login_ui_action',loginUi);
  await sleep(3500);

  let sid='';
  if(loginRequestId){
    try{ const rb=await cmd('Network.getResponseBody',{requestId:loginRequestId}); const j=JSON.parse(rb.body||'{}'); sid=j&&j.body&&j.body.sid?String(j.body.sid):''; }catch(_){ }
  }
  log('login_sid_captured_in_memory',sid?'YES':'NO');
  const cookies=await cmd('Network.getAllCookies');
  const names=[...new Set((cookies.cookies||[]).map(c=>c.name))].sort();
  log('session_identity_present',names.includes('session-identity')?'YES':'NO');
  log('session_role_present',names.includes('session-role')?'YES':'NO');
  if(!sid || !names.includes('session-identity')){ log('write_attempted','NO'); log('diagnostic','BROWSER_SESSION_PRECONDITION_FAILED'); return finish(); }

  const expr=`(async()=>{try{const body=new URLSearchParams({P212:'0',P237:${JSON.stringify(pbxIp)},sid:${JSON.stringify(sid)}}).toString();const r=await fetch('/cgi-bin/api.values.post',{method:'POST',credentials:'include',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});const t=await r.text();let j=null;try{j=JSON.parse(t)}catch(_){};return {http:r.status,response:j&&j.response||'',status:j&&j.body&&j.body.status||''};}catch(e){return {http:0,response:'',status:'NETWORK_ERROR'}}})()`;
  const wr=await cmd('Runtime.evaluate',{expression:expr,awaitPromise:true,returnByValue:true});
  const w=wr&&wr.result&&wr.result.value?wr.result.value:{};
  log('write_attempted','YES'); log('write_http',w.http||0); log('write_response',w.response||'EMPTY'); log('write_status',w.status||'EMPTY');

  const vr=await cmd('Runtime.evaluate',{expression:`(async()=>{try{const body=new URLSearchParams({request:'P212:P237',sid:${JSON.stringify(sid)}}).toString();const r=await fetch('/cgi-bin/api.values.get',{method:'POST',credentials:'include',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});const t=await r.text();let j=null;try{j=JSON.parse(t)}catch(_){};const b=j&&j.body||{};return {http:r.status,response:j&&j.response||'',p212:String(b.P212??''),p237:String(b.P237??'')};}catch(e){return {http:0,response:'',p212:'',p237:''}}})()`,awaitPromise:true,returnByValue:true});
  const v=vr&&vr.result&&vr.result.value?vr.result.value:{};
  const p212=String(v.p212)==='0'; const p237=String(v.p237)===pbxIp;
  log('verify_http',v.http||0); log('verify_response',v.response||'EMPTY'); log('p212_target_match',p212?'YES':'NO'); log('p237_target_match',p237?'YES':'NO');
  log('diagnostic',p212&&p237?'PHONE_TFTP_BOOTSTRAP_READY':'CHROMIUM_NATIVE_BOOTSTRAP_NOT_APPLIED');
  log('next_activity',p212&&p237?'G10-19F2_REBOOT_THEN_G10-19F3_PROOF':'STOP_REVIEW_BROWSER_WRITE');
  finish();

  function finish(){ log('G10-19E4E-COMPLETE','YES'); fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600}); console.log(lines.join('\n')); try{ws.close();}catch(_){ } }
})().catch(err=>{ log('diagnostic','G10-19E4E_RUNTIME_ERROR'); log('error_class',err&&err.message?String(err.message).replace(/[^A-Za-z0-9_.-]/g,'_').slice(0,120):'NODE_ERROR'); log('G10-19E4E-COMPLETE','YES'); fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600}); console.log(lines.join('\n')); process.exitCode=1; }).finally(async()=>{try{chrome.kill('SIGTERM')}catch(_){ } await sleep(300); try{fs.rmSync(profile,{recursive:true,force:true})}catch(_){ }});
