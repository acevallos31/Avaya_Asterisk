#!/usr/bin/env node
'use strict';
const http = require('http');
const fs = require('fs');
const phoneIp = process.env.PHONE_IP || '192.168.1.167';
const password = process.env.PHONE_PASSWORD || '';
const report = process.env.REPORT_PATH || '/tmp/g10-19h4-reboot.txt';
if (!password) throw new Error('PHONE_PASSWORD required');
const lines=[]; const log=(k,v)=>lines.push(`${k}=${v}`);
log('scope','CONTROLLED_REBOOT_PERSISTENCE_CHECK');
log('phone_write','REBOOT_ONLY'); log('sip_account_direct_write','NO'); log('factory_reset','NO'); log('secrets_logged','NO');
const path = `/cgi-bin/api-sys_operation?passcode=${encodeURIComponent(password)}&request=REBOOT`;
const req = http.request({host:phoneIp, port:80, method:'GET', path, headers:{Accept:'application/json'}}, res => {
  let body=''; res.on('data',c=>body+=c); res.on('end',()=>{
    let j={}; try{j=JSON.parse(body)}catch(_){}
    log('reboot_http',String(res.statusCode||0));
    log('reboot_response',j.response||'EMPTY');
    log('reboot_request',j.response==='success'?'ACCEPTED':'NOT_ACCEPTED');
    log('diagnostic',j.response==='success'?'REBOOT_ACCEPTED':'REBOOT_REJECTED');
    log('G10-19H4-REBOOT-COMPLETE','YES');
    fs.writeFileSync(report,lines.join('\n')+'\n',{mode:0o600}); console.log(lines.join('\n'));
    if(j.response!=='success') process.exitCode=1;
  });
});
req.setTimeout(10000,()=>req.destroy(new Error('timeout')));
req.on('error',e=>{log('reboot_request','ERROR');log('diagnostic','REBOOT_TRANSPORT_ERROR');log('error_class',String(e.message).replace(/[^A-Za-z0-9_.-]/g,'_'));log('G10-19H4-REBOOT-COMPLETE','YES');fs.writeFileSync(report,lines.join('\n')+'\n',{mode:0o600});console.log(lines.join('\n'));process.exitCode=1;});
req.end();
