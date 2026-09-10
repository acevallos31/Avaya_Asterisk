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

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'gxp1625-chromium-e4e-'));
const chrome = spawn('/usr/bin/chromium', [
  '--headless=new','--disable-gpu','--no-sandbox',
  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9223',
  `--user-data-dir=${profile}`,'about:blank'
], {stdio:'ignore'});

const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
log('scope','CONTROLLED_CHROMIUM_PHONE_BOOTSTRAP');
log('phone_write','P212_P237_ONLY');
log('db_write','NO'); log('pbx_live_code_write','NO'); log('factory_reset','NO'); log('secrets_logged','NO');

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function getJson(url){ return new Promise((resolve,reject)=>{ http.get(url,res=>{ let d=''; res.on('data',c=>d+=c); res.on('end',()=>{ try{resolve(JSON.parse(d))}catch(e){reject(e)} }); }).on('error',reject); }); }

(async()=>{
  let target;
  for(let i=0;i<40;i++){
    try{ const list=await getJson('http://127.0.0.1:9223/json/list'); target=list.find(x=>x.type==='page'); if(target) break; }catch(_){ }
    await sleep(200);
  }
  if(!target || !target.webSocketDebuggerUrl) throw new Error('CDP_TARGET_NOT_FOUND');
  const ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ ws.onopen=resolve; ws.onerror=reject; });
  let seq=0; const pending=new Map();
  function cmd(method,params={}){ return new Promise((resolve,reject)=>{ const id=++seq; pending.set(id,{resolve,reject}); ws.send(JSON.stringify({id,method,params})); setTimeout(()=>{ if(pending.has(id)){pending.delete(id);reject(new Error('CDP_TIMEOUT_'+method));}},7000); }); }
  ws.onmessage=(ev)=>{ let m; try{m=JSON.parse(ev.data)}catch(_){return} if(m.id&&pending.has(m.id)){ const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);} };

  await cmd('Network.enable'); await cmd('Page.enable'); await cmd('Runtime.enable');
  await cmd('Page.navigate',{url:phoneBase+'/'}); await sleep(2500);

  let loginAction='NOT_FOUND';
  for(let i=0;i<12;i++){
    const r=await cmd('Runtime.evaluate',{expression:`(()=>{
      const p=document.querySelector('input[type=password]'); if(!p) return 'NO_PASSWORD_INPUT';
      const u=document.querySelector('input[type=text],input[name*=user i],input[id*=user i]');
      if(u){u.focus();u.value=${JSON.stringify(username)};u.dispatchEvent(new Event('input',{bubbles:true}));u.dispatchEvent(new Event('change',{bubbles:true}));}
      p.focus();p.value=${JSON.stringify(password)};p.dispatchEvent(new Event('input',{bubbles:true}));p.dispatchEvent(new Event('change',{bubbles:true}));
      const f=p.closest('form'); const b=(f&&f.querySelector('button,input[type=submit]'))||[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/login|log in|sign in|entrar/i.test(x.innerText||x.value||''));
      if(b){b.click();return 'CLICKED';} if(f){if(f.requestSubmit)f.requestSubmit();else f.submit();return 'FORM_SUBMITTED';} return 'NO_SUBMIT_CONTROL';
    })()`,returnByValue:true});
    loginAction=r&&r.result&&r.result.value?r.result.value:'UNKNOWN';
    if(loginAction==='CLICKED'||loginAction==='FORM_SUBMITTED') break;
    await sleep(500);
  }
  log('login_ui_action',loginAction); await sleep(5000);

  const all=await cmd('Network.getAllCookies');
  const cookies=(all.cookies||[]).filter(c=>{ try{return new URL(phoneBase).hostname===c.domain.replace(/^\./,'');}catch(_){return true;} });
  const names=[...new Set(cookies.map(c=>c.name))].sort();
  const identity=cookies.find(c=>c.name==='session-identity');
  log('cookie_names_after_login',names.length?names.join(','):'NONE');
  log('session_identity_present',identity?'YES':'NO');
  log('session_role_present',names.includes('session-role')?'YES':'NO');
  if(!identity || !identity.value){ log('bootstrap_post_response','SKIPPED'); log('diagnostic','SESSION_IDENTITY_MISSING'); return finish(); }

  const pre=await cmd('Runtime.evaluate',{expression:`(async()=>{try{const r=await fetch('/cgi-bin/api.values.get?request=P212:P237',{credentials:'include',cache:'no-store'});const j=await r.json();return {http:r.status,response:j&&j.response||'',has212:!!(j&&j.body&&Object.prototype.hasOwnProperty.call(j.body,'P212')),has237:!!(j&&j.body&&Object.prototype.hasOwnProperty.call(j.body,'P237')),p212:String(j&&j.body?j.body.P212:''),p237:String(j&&j.body?j.body.P237:'')};}catch(e){return {error:true}}})()`,awaitPromise:true,returnByValue:true});
  const pv=pre&&pre.result&&pre.result.value?pre.result.value:{};
  log('pre_read',pv.http===200&&pv.response==='success'&&pv.has212&&pv.has237?'SUCCESS':'FAILED');
  const already=String(pv.p212)==='0'&&String(pv.p237)===pbxIp;

  if(already){
    log('phone_write_result','NO_ALREADY_CONFIGURED'); log('bootstrap_post_response','SKIPPED');
  } else {
    const wr=await cmd('Runtime.evaluate',{expression:`(async()=>{try{const body=new URLSearchParams({P212:'0',P237:${JSON.stringify(pbxIp)},sid:${JSON.stringify(identity.value)}});const r=await fetch('/cgi-bin/api.values.post',{method:'POST',credentials:'include',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body.toString()});const j=await r.json();return {http:r.status,response:j&&j.response||'',status:j&&j.body&&j.body.status||''};}catch(e){return {error:true}}})()`,awaitPromise:true,returnByValue:true});
    const wv=wr&&wr.result&&wr.result.value?wr.result.value:{};
    log('phone_write_result','ATTEMPTED'); log('bootstrap_post_http',wv.http||0); log('bootstrap_post_response',wv.response||'EMPTY'); log('bootstrap_post_status',wv.status||'EMPTY');
  }

  await sleep(1200);
  const ver=await cmd('Runtime.evaluate',{expression:`(async()=>{try{const r=await fetch('/cgi-bin/api.values.get?request=P212:P237',{credentials:'include',cache:'no-store'});const j=await r.json();return {http:r.status,response:j&&j.response||'',p212:String(j&&j.body?j.body.P212:''),p237:String(j&&j.body?j.body.P237:'')};}catch(e){return {error:true}}})()`,awaitPromise:true,returnByValue:true});
  const vv=ver&&ver.result&&ver.result.value?ver.result.value:{};
  const ok212=String(vv.p212)==='0', ok237=String(vv.p237)===pbxIp;
  log('verify_read',vv.http===200&&vv.response==='success'?'SUCCESS':'FAILED'); log('p212_target_match',ok212?'YES':'NO'); log('p237_target_match',ok237?'YES':'NO');
  log('diagnostic',ok212&&ok237?'PHONE_TFTP_BOOTSTRAP_READY':'CHROMIUM_AUTHORIZED_WRITE_NOT_ACCEPTED');
  log('next_activity',ok212&&ok237?'G10-19F_PHONE_CFG_REQUEST_PROOF':'STOP_REVIEW_E4E');
  finish();

  function finish(){ log('G10-19E4E-COMPLETE','YES'); fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600}); console.log(lines.join('\n')); try{ws.close();}catch(_){ } }
})().catch(err=>{ log('diagnostic','G10-19E4E_RUNTIME_ERROR'); log('error_class',err&&err.message?String(err.message).replace(/[^A-Za-z0-9_.-]/g,'_').slice(0,120):'NODE_ERROR'); log('G10-19E4E-COMPLETE','YES'); fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600}); console.log(lines.join('\n')); process.exitCode=1; }).finally(async()=>{ try{chrome.kill('SIGTERM')}catch(_){ } await sleep(300); try{fs.rmSync(profile,{recursive:true,force:true})}catch(_){ } });
