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
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19h8h1.txt';
if (!password) throw new Error('PHONE_PASSWORD required');

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'gxp-h8h1-'));
const chrome = spawn('/usr/bin/chromium', [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9231',
  `--user-data-dir=${profile}`, 'about:blank'
], { stdio: 'ignore' });

const lines = [];
const log = (k, v) => lines.push(`${k}=${v}`);
log('scope', 'READ_ONLY_SESSION_IDENTITY_EQUIVALENCE');
log('phone_write', 'NO');
log('db_write', 'NO');
log('pbx_live_code_write', 'NO');
log('secret_values_logged', 'NO');

const sleep = ms => new Promise(r => setTimeout(r, ms));
function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}
function safePath(raw) { try { return new URL(raw).pathname; } catch (_) { return 'UNKNOWN'; } }
function setCookieNames(raw) {
  if (!raw) return [];
  return String(raw).split(/\n|,(?=[^;,]+=)/).map(v => v.trim().split('=', 1)[0]).filter(Boolean);
}

(async () => {
  let target;
  for (let i = 0; i < 40; i++) {
    try {
      const list = await getJson('http://127.0.0.1:9231/json/list');
      target = list.find(x => x.type === 'page');
      if (target) break;
    } catch (_) {}
    await sleep(200);
  }
  if (!target?.webSocketDebuggerUrl) throw new Error('NO_CDP_TARGET');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let seq = 0;
  const pending = new Map();
  const requestPaths = new Map();
  let loginRequestId = null;
  let loginSetCookieNames = [];

  function cmd(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (pending.has(id)) {
          pending.delete(id);
          reject(new Error(`CDP_${method}_TIMEOUT`));
        }
      }, 10000);
    });
  }

  ws.onmessage = ev => {
    let m;
    try { m = JSON.parse(ev.data); } catch (_) { return; }
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result);
      return;
    }
    if (m.method === 'Network.requestWillBeSent') {
      const req = m.params?.request || {};
      const pth = safePath(req.url || '');
      requestPaths.set(m.params.requestId, pth);
      if (pth === '/cgi-bin/dologin') loginRequestId = m.params.requestId;
    }
    if (m.method === 'Network.responseReceivedExtraInfo') {
      if (requestPaths.get(m.params.requestId) !== '/cgi-bin/dologin') return;
      const headers = m.params?.headers || {};
      const raw = headers['set-cookie'] || headers['Set-Cookie'] || '';
      loginSetCookieNames = [...new Set([...loginSetCookieNames, ...setCookieNames(raw)])];
    }
  };

  await cmd('Network.enable');
  await cmd('Page.enable');
  await cmd('Runtime.enable');
  await cmd('Page.navigate', { url: `${phoneBase}/` });
  await sleep(2500);

  let action = 'NONE';
  for (let i = 0; i < 12; i++) {
    const r = await cmd('Runtime.evaluate', {
      expression: `(()=>{
        const pw=document.querySelector('input[type=password]');
        if(!pw)return 'WAIT';
        const u=document.querySelector('input[type=text],input[name*=user i],input[id*=user i]');
        if(u){u.value=${JSON.stringify(username)};u.dispatchEvent(new Event('input',{bubbles:true}));u.dispatchEvent(new Event('change',{bubbles:true}));}
        pw.value=${JSON.stringify(password)};pw.dispatchEvent(new Event('input',{bubbles:true}));pw.dispatchEvent(new Event('change',{bubbles:true}));
        const f=pw.closest('form');
        const b=(f&&f.querySelector('button,input[type=submit]'))||[...document.querySelectorAll('button,input[type=button],input[type=submit]')].find(x=>/login|log in|sign in|entrar/i.test(x.innerText||x.value||''));
        if(b){b.click();return 'CLICKED';}
        if(f){f.requestSubmit?f.requestSubmit():f.submit();return 'SUBMITTED';}
        return 'NO_SUBMIT';
      })()`,
      returnByValue: true
    });
    action = r?.result?.value || 'UNKNOWN';
    if (action === 'CLICKED' || action === 'SUBMITTED') break;
    await sleep(400);
  }
  log('login_ui_action', action);
  await sleep(4500);

  let loginSid = '';
  let loginResponse = 'UNKNOWN';
  if (loginRequestId) {
    try {
      const body = await cmd('Network.getResponseBody', { requestId: loginRequestId });
      let j = {};
      try { j = JSON.parse(body?.body || '{}'); } catch (_) {}
      loginResponse = String(j.response || 'UNKNOWN');
      loginSid = String(j.body?.sid || j.sid || '');
    } catch (_) {}
  }

  const all = await cmd('Network.getAllCookies');
  const identity = (all.cookies || []).find(c => c.name === 'session-identity');
  const role = (all.cookies || []).find(c => c.name === 'session-role');

  log('login_request_seen', loginRequestId ? 'YES' : 'NO');
  log('login_response', loginResponse);
  log('login_sid_present', loginSid ? 'YES' : 'NO');
  log('session_identity_present', identity ? 'YES' : 'NO');
  log('session_role_present', role ? 'YES' : 'NO');
  log('dologin_set_cookie_session_identity', loginSetCookieNames.includes('session-identity') ? 'YES' : 'NO');
  log('dologin_set_cookie_session_role', loginSetCookieNames.includes('session-role') ? 'YES' : 'NO');
  log('identity_equals_login_sid', identity && loginSid && identity.value === loginSid ? 'YES' : 'NO');
  if (identity) {
    log('identity_http_only', identity.httpOnly ? 'YES' : 'NO');
    log('identity_secure', identity.secure ? 'YES' : 'NO');
    log('identity_path_root', identity.path === '/' ? 'YES' : 'NO');
    log('identity_session_cookie', identity.session ? 'YES' : 'NO');
  }

  let diagnostic = 'SESSION_IDENTITY_RELATION_UNRESOLVED';
  if (identity && loginSid && identity.value === loginSid) diagnostic = 'SESSION_IDENTITY_EQUALS_LOGIN_SID';
  else if (identity && loginSid) diagnostic = 'SESSION_IDENTITY_DIFFERS_FROM_LOGIN_SID';
  else if (!identity) diagnostic = 'SESSION_IDENTITY_NOT_PRESENT';
  else if (!loginSid) diagnostic = 'LOGIN_SID_NOT_EXTRACTED';
  log('diagnostic', diagnostic);
  log('G10-19H8H1-COMPLETE', 'YES');

  fs.writeFileSync(reportPath, lines.join('\n') + '\n', { mode: 0o600 });
  console.log(lines.join('\n'));
  try { ws.close(); } catch (_) {}
})().catch(e => {
  log('diagnostic', 'RUNTIME_ERROR');
  log('error_class', String(e.message || e).replace(/[^A-Za-z0-9_.-]/g, '_').slice(0, 100));
  log('G10-19H8H1-COMPLETE', 'YES');
  fs.writeFileSync(reportPath, lines.join('\n') + '\n', { mode: 0o600 });
  console.log(lines.join('\n'));
  process.exitCode = 1;
}).finally(async () => {
  try { chrome.kill('SIGTERM'); } catch (_) {}
  await sleep(200);
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
});
