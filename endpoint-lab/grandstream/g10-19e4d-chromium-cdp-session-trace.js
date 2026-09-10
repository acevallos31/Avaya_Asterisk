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
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19e4d.txt';
if (!password) throw new Error('PHONE_PASSWORD is required');

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'gxp1625-chromium-'));
const chrome = spawn('/usr/bin/chromium', [
  '--headless=new','--disable-gpu','--no-sandbox',
  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9222',
  `--user-data-dir=${profile}`,'about:blank'
], {stdio:'ignore'});

const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
log('scope','READ_ONLY_CHROMIUM_CDP_SESSION_TRACE');
log('phone_write','NO'); log('db_write','NO'); log('pbx_live_code_write','NO'); log('secrets_logged','NO');

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function getJson(url){
  return new Promise((resolve,reject)=>{
    http.get(url,res=>{ let d=''; res.on('data',c=>d+=c); res.on('end',()=>{ try{resolve(JSON.parse(d))}catch(e){reject(e)} }); }).on('error',reject);
  });
}
function safePath(raw){ try{ return new URL(raw).pathname; }catch(_){ return 'UNKNOWN'; } }
function cookieNamesFromHeader(h){
  if(!h) return [];
  return String(h).split(';').map(x=>x.trim().split('=',1)[0]).filter(Boolean);
}
function setCookieNames(headers){
  const vals=[];
  for (const [k,v] of Object.entries(headers||{})) if (k.toLowerCase()==='set-cookie') vals.push(String(v));
  const out=[];
  for(const v of vals){ for(const part of v.split(/\n|,(?=[^;,]+=)/)){ const n=part.trim().split('=',1)[0]; if(n) out.push(n); } }
  return out;
}

(async()=>{
  let target;
  for(let i=0;i<30;i++){
    try{
      const list=await getJson('http://127.0.0.1:9222/json/list');
      target=list.find(x=>x.type==='page'); if(target) break;
    }catch(_){ }
    await sleep(200);
  }
  if(!target || !target.webSocketDebuggerUrl) throw new Error('CDP_TARGET_NOT_FOUND');

  const ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ ws.onopen=resolve; ws.onerror=reject; });
  let seq=0; const pending=new Map();
  function cmd(method,params={}){
    return new Promise((resolve,reject)=>{
      const id=++seq; pending.set(id,{resolve,reject}); ws.send(JSON.stringify({id,method,params}));
      setTimeout(()=>{ if(pending.has(id)){pending.delete(id); reject(new Error('CDP_TIMEOUT_'+method));}},5000);
    });
  }
  let firstIdentityPath='NONE';
  let identitySeen=false;
  let roleSeen=false;
  let setIdentitySeen=false;
  let requestCount=0;
  ws.onmessage=(ev)=>{
    let m; try{m=JSON.parse(ev.data)}catch(_){return}
    if(m.id && pending.has(m.id)){ const p=pending.get(m.id); pending.delete(m.id); m.error?p.reject(new Error(m.error.message)):p.resolve(m.result); return; }
    if(m.method==='Network.requestWillBeSentExtraInfo'){
      requestCount++;
      const h=m.params&&m.params.headers?m.params.headers:{};
      const ck=h.Cookie||h.cookie||'';
      const names=cookieNamesFromHeader(ck);
      if(names.includes('session-role')) roleSeen=true;
      if(names.includes('session-identity')) identitySeen=true;
    }
    if(m.method==='Network.requestWillBeSent'){
      const req=m.params&&m.params.request?m.params.request:{};
      const h=req.headers||{}; const names=cookieNamesFromHeader(h.Cookie||h.cookie||'');
      if(names.includes('session-role')) roleSeen=true;
      if(names.includes('session-identity')){
        identitySeen=true;
        if(firstIdentityPath==='NONE') firstIdentityPath=safePath(req.url||'');
      }
    }
    if(m.method==='Network.responseReceivedExtraInfo'){
      const names=setCookieNames((m.params&&m.params.headers)||{});
      if(names.includes('session-identity')) setIdentitySeen=true;
    }
  };

  await cmd('Network.enable'); await cmd('Page.enable'); await cmd('Runtime.enable');
  await cmd('Page.navigate',{url:phoneBase+'/'});
  await sleep(2500);

  let loginUi='NOT_FOUND';
  for(let i=0;i<12;i++){
    const r=await cmd('Runtime.evaluate',{expression:`(()=>{
      const p=document.querySelector('input[type=password]');
      if(!p) return 'NO_PASSWORD_INPUT';
      const u=document.querySelector('input[type=text],input[name*=user i],input[id*=user i]');
      if(u){u.focus();u.value=${JSON.stringify(username)};u.dispatchEvent(new Event('input',{bubbles:true}));u.dispatchEvent(new Event('change',{bubbles:true}));}
      p.focus();p.value=${JSON.stringify(password)};p.dispatchEvent(new Event('input',{bubbles:true}));p.dispatchEvent(new Event('change',{bubbles:true}));
      const f=p.closest('form');
      const b=(f&&f.querySelector('button,input[type=submit]'))||[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/login|log in|sign in|entrar/i.test(x.innerText||x.value||''));
      if(b){b.click();return 'CLICKED';}
      if(f){if(f.requestSubmit)f.requestSubmit();else f.submit();return 'FORM_SUBMITTED';}
      return 'NO_SUBMIT_CONTROL';
    })()`,returnByValue:true});
    loginUi=r&&r.result&&r.result.value?r.result.value:'UNKNOWN';
    if(loginUi==='CLICKED'||loginUi==='FORM_SUBMITTED') break;
    await sleep(500);
  }
  log('login_ui_action',loginUi);
  await sleep(5000);

  const cookies=await cmd('Network.getAllCookies');
  const names=[...new Set((cookies.cookies||[]).map(c=>c.name))].sort();
  log('cookie_names_after_login',names.length?names.join(','):'NONE');
  log('session_role_seen',roleSeen||names.includes('session-role')?'YES':'NO');
  log('session_identity_seen',identitySeen||names.includes('session-identity')?'YES':'NO');
  log('session_identity_set_cookie_seen',setIdentitySeen?'YES':'NO');
  log('first_session_identity_request_path',firstIdentityPath);
  log('network_request_events',requestCount);

  if(identitySeen||names.includes('session-identity')){
    log('diagnostic','SESSION_IDENTITY_CREATED_IN_REAL_CHROMIUM_FLOW');
    log('next_activity','G10-19E4E_REPLAY_BROWSER_SEQUENCE_WITHOUT_SECRET_VALUES');
  } else {
    log('diagnostic','SESSION_IDENTITY_NOT_CREATED_BY_AUTOMATED_LOGIN_UI');
    log('next_activity','G10-19E4E_INSPECT_LOGIN_FLOW_EVENTS');
  }
  log('G10-19E4D-COMPLETE','YES');
  fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});
  console.log(lines.join('\n'));
  try{ws.close();}catch(_){ }
})().catch(err=>{
  log('diagnostic','G10-19E4D_RUNTIME_ERROR'); log('error_class',err&&err.message?String(err.message).replace(/[^A-Za-z0-9_.-]/g,'_').slice(0,120):'NODE_ERROR'); log('G10-19E4D-COMPLETE','YES');
  fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600}); console.log(lines.join('\n')); process.exitCode=1;
}).finally(async()=>{ try{chrome.kill('SIGTERM')}catch(_){ } await sleep(300); try{fs.rmSync(profile,{recursive:true,force:true})}catch(_){ } });
