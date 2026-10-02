import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { acquireAdmission } from '../server/admission.mjs';
import { createGateway } from '../server/gateway.mjs';
const secret='CONTROLLER_TEST_ONLY_01234567890123456789';
const env={NODE_ENV:'production',SONAR_ADMISSION_URL:'https://controller.invalid',SONAR_ADMISSION_TOKEN:secret,APP_ORIGIN:'https://sonarshield26.vercel.app',HF_TOKEN:'hf_TESTONLYNOTAREALCREDENTIAL'};
test('durable admission sends controller credential only to configured service and releases opaque lease',async()=>{
  const calls=[];const lease=await acquireAdmission(env,async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify({lease_id:'a'.repeat(32)}));});
  await lease.release();assert.equal(calls.length,2);assert.equal(calls[0].options.headers.Authorization,`Bearer ${secret}`);assert.equal(calls[0].options.redirect,'error');assert.equal(JSON.parse(calls[1].options.body).lease_id,'a'.repeat(32));
});
test('misconfiguration, offline controller and rejection fail closed before any HF connect',async()=>{
  for(const setting of [{SONAR_ADMISSION_URL:'http://foreign.invalid'}, {SONAR_ADMISSION_TOKEN:''}, {}, {offline:true}]){
    let connected=0;
    const res=new EventEmitter();res.setHeader=()=>{};res.end=value=>{res.body=JSON.parse(value);res.writableEnded=true;};
    const req={method:'POST',headers:{origin:env.APP_ORIGIN,'sec-fetch-site':'same-origin','content-type':'application/json'},body:{file:{path:`/tmp/gradio/${'a'.repeat(64)}/image.jpg`,mime_type:'image/jpeg',orig_name:'image.jpg',size:100}}};
    await createGateway({env:{...env,...setting},connect:async()=>{connected++;throw Error('Should not connect');},fetcher:async()=>{if(setting.offline)throw Error('Offline');return new Response('{}',{status:429});}})(req,res);
    assert.equal(connected,0);assert.ok(['LIVE_USAGE_LIMIT','LIVE_LIMITER_UNAVAILABLE'].includes(res.body.error.code));assert.ok(!JSON.stringify(res.body).includes(secret));
  }
});
