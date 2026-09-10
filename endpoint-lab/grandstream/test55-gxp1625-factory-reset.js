#!/usr/bin/env node
'use strict';

const {spawn}=require('child_process');
const http=require('http');
const fs=require('fs');
const os=require('os');
const path=require('path');

const phoneBase=process.env.PHONE_BASE||'http://192.168.1.167';
const username=process.env.PHONE_USERNAME||'admin';
const password=process.env.PHONE_PASSWORD||'';
const reportPath=process.env.REPORT_PATH||'/tmp/test55-factory-reset.txt';
if(!password) throw new Error('PHONE_PASSWORD required');

const profile=fs.mkdtempSync(path.join(os.tmpdir(),'gxp1625-test55-'));
const chrome=spawn('/usr/bin/chromium',[
  '--headless=new','--disable-gpu','--no-sandbox',
  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9255',
  `--user-data-dir=${profile}`,'about:blank'
],{stdio:'ignore'});
const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
log('scope','TEST55_CONTROLLED_GXP1625_FACTORY_RESET');
log('target_ip','192.168.1.167');
log('target_mac','C0:74:AD:E8:66:09');
log('phone_write','FACTORY_RESET_ONLY');
log('secrets_logged','NO');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJson=url=>new Promise((resolve,reject)=>http.get(url,res=>{let d='';res.on('data',c=>d+=c);res.on('end',()=>{try{resolve(JSON.parse(d))}catch(e){reject(e)}})}).on('error',reject));
const phoneReachable=()=>new Promise(resolve=>{const u=new URL(phoneBase+'/');const q=http.get({host:u.hostname,port:u.port||80,path:'/',timeout:2500},res=>{res.resume();resolve(true)});q.on('timeout',()=>q.destroy());q.on('error',()=>resolve(false));});

(async()=>{
  let target;
  for(let i=0;i<40;i++){
    try{const list=await getJson('http://127.0.0.1:9255/json/list');target=list.find(x=>x.type==='page');if(target)break;}catch(_){}
    await sleep(200);
  }
  if(!target) throw new Error('CDP_TARGET_NOT_FOUND');
  const ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let seq=0; const pending=new Map(); let resetClicked=false; let dialogAccepted=false;
  function cmd(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(new Error('CDP_TIMEOUT_'+method));}},10000);});}
  ws.onmessage=ev=>{let m;try{m=JSON.parse(ev.data)}catch(_){return}if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);return;}if(m.method==='Page.javascriptDialogOpening'&&resetClicked){dialogAccepted=true;cmd('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});}};

  await cmd('Network.enable'); await cmd('Page.enable'); await cmd('Runtime.enable');
  await cmd('Page.navigate',{url:phoneBase+'/'}); await sleep(2500);
  let loginAction='NOT_FOUND';
  for(let i=0;i<12;i++){
    const r=await cmd('Runtime.evaluate',{expression:`(()=>{const p=document.querySelector('input[type=password]');if(!p)return 'NO_PASSWORD_INPUT';const u=document.querySelector('input[type=text],input[name*=user i],input[id*=user i]');if(u){u.value=${JSON.stringify(username)};u.dispatchEvent(new Event('input',{bubbles:true}));u.dispatchEvent(new Event('change',{bubbles:true}));}p.value=${JSON.stringify(password)};p.dispatchEvent(new Event('input',{bubbles:true}));p.dispatchEvent(new Event('change',{bubbles:true}));const f=p.closest('form');const b=(f&&f.querySelector('button,input[type=submit]'))||[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/login|log in|sign in|entrar/i.test(x.innerText||x.value||''));if(b){b.click();return 'CLICKED';}if(f){f.requestSubmit?f.requestSubmit():f.submit();return 'FORM_SUBMITTED';}return 'NO_SUBMIT';})()`,returnByValue:true});
    loginAction=r?.result?.value||'UNKNOWN';
    if(loginAction==='CLICKED'||loginAction==='FORM_SUBMITTED') break;
    await sleep(500);
  }
  log('login_ui_action',loginAction); await sleep(5000);
  const cookies=await cmd('Network.getAllCookies');
  const cookieNames=[...new Set((cookies.cookies||[]).map(c=>c.name))];
  log('session_identity_present',cookieNames.includes('session-identity')?'YES':'NO');
  if(!cookieNames.includes('session-identity')) throw new Error('AUTHENTICATED_SESSION_NOT_ESTABLISHED');

  const locate=await cmd('Runtime.evaluate',{expression:`(()=>{const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};const els=[...document.querySelectorAll('button,a,input[type=button],input[type=submit]')].filter(visible);const matches=els.filter(e=>/factory\\s*reset|reset\\s*(to\\s*)?factory/i.test([e.innerText,e.value,e.title,e.getAttribute('aria-label')].filter(Boolean).join(' ')));return {count:matches.length,labels:matches.map(e=>(e.innerText||e.value||e.title||e.getAttribute('aria-label')||'').trim().slice(0,80))};})()`,returnByValue:true});
  const located=locate?.result?.value||{};
  log('factory_reset_control_count',String(located.count||0));
  if(located.count!==1) throw new Error('FACTORY_RESET_CONTROL_NOT_UNIQUE');

  resetClicked=true;
  const clicked=await cmd('Runtime.evaluate',{expression:`(()=>{const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};const matches=[...document.querySelectorAll('button,a,input[type=button],input[type=submit]')].filter(visible).filter(e=>/factory\\s*reset|reset\\s*(to\\s*)?factory/i.test([e.innerText,e.value,e.title,e.getAttribute('aria-label')].filter(Boolean).join(' ')));if(matches.length!==1)return 'NOT_UNIQUE';matches[0].click();return 'CLICKED';})()`,returnByValue:true});
  log('factory_reset_control_action',clicked?.result?.value||'UNKNOWN');
  await sleep(1800);

  if(!dialogAccepted){
    const confirm=await cmd('Runtime.evaluate',{expression:`(()=>{const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};const containers=[...document.querySelectorAll('[role=dialog],.modal,.dialog')].filter(visible).filter(e=>/factory|reset/i.test(e.innerText||''));const buttons=containers.flatMap(c=>[...c.querySelectorAll('button,input[type=button],input[type=submit]')]).filter(visible).filter(e=>/^(ok|yes|confirm|reset|factory reset)$/i.test((e.innerText||e.value||'').trim()));if(buttons.length===1){buttons[0].click();return 'CLICKED';}return buttons.length===0?'NO_MODAL_CONFIRM':'NOT_UNIQUE';})()`,returnByValue:true});
    log('factory_reset_modal_action',confirm?.result?.value||'UNKNOWN');
  }else log('factory_reset_dialog_action','ACCEPTED');

  let wentDown=false;
  for(let i=0;i<45;i++){if(!(await phoneReachable())){wentDown=true;break;}await sleep(2000);}
  log('phone_http_went_down',wentDown?'YES':'NO');
  if(!wentDown) throw new Error('PHONE_DID_NOT_REBOOT');
  let returned=false;
  for(let i=0;i<90;i++){if(await phoneReachable()){returned=true;break;}await sleep(3000);}
  log('phone_http_returned',returned?'YES':'NO');
  if(!returned) throw new Error('PHONE_DID_NOT_RETURN');
  log('factory_reset_observed','YES');
  log('TEST55-FACTORY-RESET','PASS');
  fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});
  console.log(lines.join('\n'));
  try{ws.close()}catch(_){}
})().catch(e=>{log('diagnostic',String(e.message).replace(/[^A-Za-z0-9_.-]/g,'_'));log('TEST55-FACTORY-RESET','FAIL');fs.writeFileSync(reportPath,lines.join('\n')+'\n',{mode:0o600});console.log(lines.join('\n'));process.exitCode=1;}).finally(async()=>{try{chrome.kill('SIGTERM')}catch(_){}await sleep(300);try{fs.rmSync(profile,{recursive:true,force:true})}catch(_){}});
