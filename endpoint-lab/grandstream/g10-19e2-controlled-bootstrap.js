#!/usr/bin/env node
'use strict';

const http = require('http');
const fs = require('fs');
const { URLSearchParams } = require('url');

const phoneIp = process.env.PHONE_IP || '192.168.1.167';
const username = process.env.PHONE_USERNAME || 'admin';
const password = process.env.PHONE_PASSWORD || '';
const pbxIp = process.env.PBX_IP || '192.168.1.10';
const reportPath = process.env.REPORT_PATH || '/tmp/g10-19e2-controlled-bootstrap.txt';

if (!password) throw new Error('PHONE_PASSWORD is required');

const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
let cookies = [];
let firstSocket = null;
let reusedAll = true;

function addCookies(res) {
  const set = res.headers['set-cookie'] || [];
  for (const raw of set) {
    const pair = String(raw).split(';', 1)[0];
    const name = pair.split('=', 1)[0];
    cookies = cookies.filter(x => !x.startsWith(name + '='));
    cookies.push(pair);
  }
}

function req(path, body) {
  return new Promise((resolve, reject) => {
    const data = new URLSearchParams(body).toString();
    const headers = {
      'Host': phoneIp,
      'Referer': `http://${phoneIp}/`,
      'Origin': `http://${phoneIp}`,
      'User-Agent': 'Mozilla/5.0',
      'Accept': '*/*',
      'Content-Type': 'application/x-www-form-urlencoded',
      'Content-Length': Buffer.byteLength(data),
      'Connection': 'keep-alive'
    };
    if (cookies.length) headers['Cookie'] = cookies.join('; ');
    const r = http.request({ host: phoneIp, port: 80, path, method: 'POST', headers, agent }, res => {
      addCookies(res);
      let txt = '';
      res.setEncoding('utf8');
      res.on('data', c => txt += c);
      res.on('end', () => resolve({ status: res.statusCode, text: txt, headers: res.headers }));
    });
    r.on('socket', sock => {
      if (!firstSocket) firstSocket = sock;
      else if (sock !== firstSocket) reusedAll = false;
    });
    r.on('error', reject);
    r.end(data);
  });
}

function parseJson(r) {
  try { return JSON.parse(r.text); } catch (_) { return null; }
}

function bodyObj(j) {
  return j && typeof j.body === 'object' && j.body ? j.body : {};
}

(async () => {
  const out = [];
  const log = (k,v) => out.push(`${k}=${v}`);
  log('scope','CONTROLLED_PHONE_BOOTSTRAP');
  log('db_write','NO');
  log('pbx_live_code_write','NO');
  log('factory_reset','NO');
  log('target','GXP1625');

  const login = await req('/cgi-bin/dologin', { username, password });
  const lj = parseJson(login);
  const sid = lj && lj.body && lj.body.sid ? String(lj.body.sid) : '';
  log('login', login.status === 200 && lj && lj.response === 'success' && sid ? 'SUCCESS' : 'FAILED');
  log('login_http', login.status);
  if (!sid) {
    log('phone_write','NO');
    log('diagnostic','BOOTSTRAP_LOGIN_FAILED');
    log('G10-19E2-COMPLETE','YES');
    fs.writeFileSync(reportPath, out.join('\n')+'\n', {mode:0o600});
    console.log(out.join('\n'));
    return;
  }

  const before = await req('/cgi-bin/api.values.get', { request: 'P212:P237', sid });
  const bj = parseJson(before);
  const bo = bodyObj(bj);
  const beforeOk = before.status === 200 && bj && bj.response === 'success' && Object.prototype.hasOwnProperty.call(bo,'P212') && Object.prototype.hasOwnProperty.call(bo,'P237');
  log('pre_read', beforeOk ? 'SUCCESS' : 'FAILED');
  log('pre_read_http', before.status);
  log('p212_before_present', Object.prototype.hasOwnProperty.call(bo,'P212') ? 'YES' : 'NO');
  log('p237_before_present', Object.prototype.hasOwnProperty.call(bo,'P237') ? 'YES' : 'NO');
  if (!beforeOk) {
    log('phone_write','NO');
    log('diagnostic','BOOTSTRAP_PRE_READ_FAILED');
    log('connection_reused', reusedAll ? 'YES' : 'NO');
    log('G10-19E2-COMPLETE','YES');
    fs.writeFileSync(reportPath, out.join('\n')+'\n', {mode:0o600});
    console.log(out.join('\n'));
    return;
  }

  const already = String(bo.P212) === '0' && String(bo.P237) === pbxIp;
  if (already) {
    log('phone_write','NO_ALREADY_CONFIGURED');
    log('bootstrap_post','SKIPPED');
  } else {
    const wr = await req('/cgi-bin/api.values.post', { P212: '0', P237: pbxIp, sid });
    const wj = parseJson(wr);
    const status = wj && wj.body && wj.body.status ? String(wj.body.status) : 'EMPTY';
    log('phone_write','YES_CONTROLLED_P212_P237');
    log('bootstrap_post_http', wr.status);
    log('bootstrap_post_response', wj && wj.response ? String(wj.response) : 'EMPTY');
    log('bootstrap_post_status', status);
  }

  const verify = await req('/cgi-bin/api.values.get', { request: 'P212:P237', sid });
  const vj = parseJson(verify);
  const vo = bodyObj(vj);
  const verified = verify.status === 200 && vj && vj.response === 'success' && String(vo.P212) === '0' && String(vo.P237) === pbxIp;
  log('verify_read', verify.status === 200 && vj && vj.response === 'success' ? 'SUCCESS' : 'FAILED');
  log('verify_http', verify.status);
  log('p212_target_match', String(vo.P212) === '0' ? 'YES' : 'NO');
  log('p237_target_match', String(vo.P237) === pbxIp ? 'YES' : 'NO');
  log('connection_reused', reusedAll ? 'YES' : 'NO');
  log('diagnostic', verified ? 'PHONE_TFTP_BOOTSTRAP_READY' : 'PHONE_TFTP_BOOTSTRAP_NOT_APPLIED');
  log('next_activity', verified ? 'G10-19F_PHONE_CFG_REQUEST_PROOF' : 'G10-19E3_EXACT_WRITE_DIAGNOSTIC');
  log('G10-19E2-COMPLETE','YES');
  fs.writeFileSync(reportPath, out.join('\n')+'\n', {mode:0o600});
  console.log(out.join('\n'));
  agent.destroy();
})().catch(err => {
  const msg = [
    'scope=CONTROLLED_PHONE_BOOTSTRAP',
    'phone_write=UNKNOWN',
    'diagnostic=G10-19E2_RUNTIME_ERROR',
    'error_class=' + (err && err.code ? err.code : 'NODE_ERROR'),
    'G10-19E2-COMPLETE=YES'
  ].join('\n') + '\n';
  fs.writeFileSync(reportPath, msg, {mode:0o600});
  console.log(msg.trim());
  process.exitCode = 1;
});
