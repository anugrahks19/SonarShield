import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {seedJudgeDemo,judgeDemoExamples} from '../shared/judge-demo.mjs';
const fetcher=async url=>url.endsWith('.json')?Response.json(JSON.parse(readFileSync(new URL('../public'+url,import.meta.url)))):new Response(readFileSync(new URL('../public'+url,import.meta.url)));
test('three paired precomputed records seed once and preserve judge history without inference',async()=>{
 const records=new Map();const calls=[];let uploads=0;
 const api=async body=>{calls.push(body);if(body.action==='create'){assert.equal(body.source,'PRECOMPUTED_EXAMPLE');assert.equal(body.team_id,null);const e=judgeDemoExamples.find(e=>e.analysisId===body.analysis.analysis_id);assert.equal(body.image_sha256,e.imageHash);if(!records.has(e.analysisId))records.set(e.analysisId,{id:e.analysisId,image_path:e.slug,review_history:[]});return records.get(e.analysisId);}const record=records.get(body.id);if(body.action==='review'){assert.match(body.note,/DEMO SEED/);record.review_history.push(body);}return record;};
 const options={api,fetcher,upload:async()=>uploads++};await seedJudgeDemo(options);records.get(judgeDemoExamples[0].analysisId).review_history.push({note:'judge note'});await seedJudgeDemo(options);
 assert.equal(records.size,3);assert.equal(uploads,6);assert.deepEqual([...records.values()].map(r=>r.review_history.length),[3,2,2]);assert.ok(calls.every(c=>['create','get','review'].includes(c.action)));
});
test('tampered sample is rejected before cloud writes',async()=>{let writes=0;await assert.rejects(seedJudgeDemo({api:async()=>writes++,upload:async()=>writes++,fetcher:async url=>url.endsWith('.json')?fetcher(url):new Response('bad bytes')}),/pairing/);assert.equal(writes,0);});
