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
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19e4f.txt';
if (!password) throw new Error('PHONE_PASSWORD is required');

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'gxp1625-ui-save-'));
const chrome = spawn('/usr/bin/chromium', [
  '--headless=new','--disable-gpu','--no-sandbox',
  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9224',
  `--user-data-dir=${profile}`,'about:blank'
], {stdio:'ignore'});

const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
log('scope','CONTROLLED_CHROMIUM_UI_SAVE_AND_APPLY');
log('phone_write','P212_P237_SAME_TARGET_VIA_UI');
log('factory_reset','NO'); log('db_write','NO'); log('pbx_live_code_write','NO'); log('secrets_logged','NO');
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
function getJson(url){return new Promise((resolve,reject)=>{http.get(url,res=>{let d='';res.on('data',c=>d+=c);res.on('end',()=>{try{resolve(JSON.parse(d))}catch(e){reject(e)}})}).on('error',reject);});}
function cleanPath(u){try{return new URL(u).pathname}catch(_){return 'UNKNOWN'}}

(async()=>{
  let target;
  for(let i=0;i<30;i++){try{const a=await getJson('http://127.0.0.1:9224/json/list');target=a.find(x=>x.type==='page');if(target)break;}catch(_){}await sleep(200);}
  if(!target?.webSocketDebuggerUrl) throw new Error('CDP_TARGET_NOT_FOUND');
  const ws=new WebSocket(target.webSocketDebuggerUrl); await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej});
  let seq=0; const pending=new Map(); const apiEvents=[];
  function cmd(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(new Error('CDP_TIMEOUT_'+method));}},8000);});}
  ws.onmessage=(ev)=>{let m;try{m=JSON.parse(ev.data)}catch(_){return}if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);return;}if(m.method==='Network.requestWillBeSent'){const r=m.params?.request||{};const p=cleanPath(r.url||'');if(p.startsWith('/cgi-bin/')) apiEvents.push(`${r.method||'GET'} ${p}`);}};
  await cmd('Network.enable'); await cmd('Page.enable'); await cmd('Runtime.enable');
  await cmd('Page.navigate',{url:phoneBase+'/'}); await sleep(2200);

  let loginUi='NOT_FOUND';
  for(let i=0;i<12;i++){
    const r=await cmd('Runtime.evaluate',{expression:`(()=>{const p=document.querySelector('input[type=password]');if(!p)return 'NO_PASSWORD_INPUT';const u=document.querySelector('input[type=text],input[name*=user i],input[id*=user i]');if(u){u.value=${JSON.stringify(username)};u.dispatchEvent(new Event('input',{bubbles:true}));u.dispatchEvent(new Event('change',{bubbles:true}));}p.value=${JSON.stringify(password)};p.dispatchEvent(new Event('input',{bubbles:true}));p.dispatchEvent(new Event('change',{bubbles:true}));const f=p.closest('form');const b=(f&&f.querySelector('button,input[type=submit]'))||[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/login|log in|sign in|entrar/i.test(x.innerText||x.value||''));if(b){b.click();return 'CLICKED';}if(f){f.requestSubmit?f.requestSubmit():f.submit();return 'FORM_SUBMITTED';}return 'NO_SUBMIT';})()`,returnByValue:true});
    loginUi=r?.result?.value||'UNKNOWN'; if(/CLICKED|FORM_SUBMITTED/.test(loginUi))break; await sleep(400);
  }
  log('login_ui_action',loginUi); await sleep(3500);
  const ck=await cmd('Network.getAllCookies'); const names=[...new Set((ck.cookies||[]).map(c=>c.name))];
  log('session_identity_present',names.includes('session-identity')?'YES':'NO');
  if(!names.includes('session-identity')){log('ui_change_attempted','NO');log('diagnostic','SESSION_PRECONDITION_FAILED');return finish();}

  await cmd('Page.navigate',{url:phoneBase+'/#page:maintenance_upgrade'}); await sleep(3500);
  const probe=await cmd('Runtime.evaluate',{expression:`(()=>{const text=document.body.innerText||'';return {hasUpgrade:/Upgrade and Provisioning/i.test(text),hasConfigVia:/Config Upgrade Via/i.test(text),hasConfigPath:/Config Server Path/i.test(text),hasSaveApply:/Save and Apply/i.test(text)};})()`,returnByValue:true});
  const pv=probe?.result?.value||{};
  log('page_upgrade_visible',pv.hasUpgrade?'YES':'NO'); log('config_upgrade_via_visible',pv.hasConfigVia?'YES':'NO'); log('config_server_path_visible',pv.hasConfigPath?'YES':'NO'); log('save_and_apply_visible',pv.hasSaveApply?'YES':'NO');
  if(!pv.hasConfigVia||!pv.hasConfigPath||!pv.hasSaveApply){log('ui_change_attempted','NO');log('diagnostic','PROVISIONING_UI_NOT_LOCATED');return finish();}

  apiEvents.length=0;
  const act=await cmd('Runtime.evaluate',{expression:`(()=>{
    function rowFor(rx){const all=[...document.querySelectorAll('div,td,tr,li,label,span')].filter(e=>rx.test((e.innerText||'').trim()));for(const e of all){let n=e;for(let i=0;i<6&&n;i++,n=n.parentElement){if(n.querySelector&&n.querySelector('input,select'))return n;}}return null;}
    const viaRow=rowFor(/^Config Upgrade Via$/i)||rowFor(/Config Upgrade Via/i); const pathRow=rowFor(/^Config Server Path$/i)||rowFor(/Config Server Path/i);
    const sel=viaRow&&viaRow.querySelector('select'); const inp=pathRow&&pathRow.querySelector('input[type=text],input:not([type])');
    let via='NO_SELECT',pth='NO_INPUT';
    if(sel){const opt=[...sel.options].find(o=>/TFTP/i.test(o.textContent||''));if(opt){sel.value=opt.value;sel.dispatchEvent(new Event('change',{bubbles:true}));via='SET_TFTP';}}
    if(inp){inp.focus();inp.value=${JSON.stringify(pbxIp)};inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}));pth='SET_PBX';}
    const btn=[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/Save and Apply/i.test(x.innerText||x.value||''));
    if(btn&&via==='SET_TFTP'&&pth==='SET_PBX'){btn.click();return {via,pth,clicked:true};}
    return {via,pth,clicked:false};
  })()`,returnByValue:true});
  const av=act?.result?.value||{}; log('ui_set_config_via',av.via||'UNKNOWN'); log('ui_set_config_path',av.pth||'UNKNOWN'); log('save_and_apply_clicked',av.clicked?'YES':'NO'); log('ui_change_attempted',av.clicked?'YES':'NO');
  await sleep(5000);
  const unique=[...new Set(apiEvents)].slice(0,20); log('cgi_request_count',apiEvents.length); log('cgi_unique_paths',unique.length?unique.join('|'):'NONE');
  log('diagnostic',av.clicked?'UI_SAVE_AND_APPLY_TRIGGERED':'UI_SAVE_AND_APPLY_NOT_TRIGGERED');
  log('next_activity',av.clicked?'G10-19E4G_VERIFY_PERSISTENCE_AFTER_UI_APPLY':'STOP_REVIEW_UI_MAPPING');
  finish();

  function finish(){log('G10-19E4F-COMPLETE','YES');fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});console.log(lines.join('\n'));try{ws.close()}catch(_){}}
})().catch(err=>{log('diagnostic','G10-19E4F_RUNTIME_ERROR');log('error_class',String(err?.message||'NODE_ERROR').replace(/[^A-Za-z0-9_.-]/g,'_').slice(0,120));log('G10-19E4F-COMPLETE','YES');fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});console.log(lines.join('\n'));process.exitCode=1;}).finally(async()=>{try{chrome.kill('SIGTERM')}catch(_){}await sleep(300);try{fs.rmSync(profile,{recursive:true,force:true})}catch(_){}});
