import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {seedJudgeDemo,judgeDemo} from '../shared/judge-demo.mjs';
const sample=JSON.parse(readFileSync(new URL('../public/contact-105.json',import.meta.url)));
const image=readFileSync(new URL('../public/contact-105.jpg',import.meta.url));
test('judge seed is paired precomputed only, adds labeled history once and never calls inference',async()=>{
 const calls=[];let history=[];
 const api=async body=>{calls.push(body);if(body.action==='create'){assert.equal(body.source,'PRECOMPUTED_EXAMPLE');assert.equal(body.team_id,null);assert.equal(body.image_sha256,judgeDemo.imageHash);return {id:'seed',image_path:'seed/image.jpg'};}if(body.action==='review'){assert.match(body.note,/DEMO SEED/);history.push(body);return {};}return {review_history:history};};
 const fetcher=async url=>{assert.ok(['/contact-105.json','/contact-105.jpg'].includes(url));return url.endsWith('.json')?Response.json(sample):new Response(image);};
 let uploads=0;const options={api,fetcher,upload:async()=>uploads++};await seedJudgeDemo(options);await seedJudgeDemo(options);
 assert.equal(history.length,2);assert.equal(uploads,2);assert.ok(calls.every(c=>['create','get','review'].includes(c.action)));
});
test('tampered sample is rejected before any cloud writes',async()=>{
 let writes=0;await assert.rejects(seedJudgeDemo({api:async()=>writes++,upload:async()=>writes++,fetcher:async url=>url.endsWith('.json')?Response.json(sample):new Response('bad bytes')}),/pairing/);assert.equal(writes,0);
});
