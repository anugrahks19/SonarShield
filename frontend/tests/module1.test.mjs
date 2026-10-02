import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { analyzeSchema } from '../src/api/schema.ts';
import { exportCsvText } from '../src/reports/export.ts';
import { validateFile, validateMetadata } from '../server/gateway.mjs';
const historical=JSON.parse(readFileSync(new URL('../public/contact-105.json',import.meta.url),'utf8'));
test('expanded CSV contains dimensions and protected reviewer notes',()=>{
  const c=historical.candidates[0];
  const csv=exportCsvText(historical,{[c.candidate_id]:{analysisId:historical.analysis_id,candidateId:c.candidate_id,status:'CONFIRMED',reviewedAt:'2026-10-02T00:00:00Z',note:'=EVIL()'}});
  assert.match(csv,/width_px,height_px,area_px/);assert.match(csv,/human_note/);assert.match(csv,/'=EVIL/);
});
test('metadata is bounded and image size checked without accepting arbitrary references',()=>{
  assert.equal(validateMetadata({}),undefined);
  assert.throws(()=>validateMetadata({metadata_json:'[]'}));
  assert.throws(()=>validateMetadata({metadata_json:'x'.repeat(300000)}));
  assert.throws(()=>validateFile({file:{path:'/tmp/gradio/'+ 'a'.repeat(64)+'/a.jpg',orig_name:'a.jpg',mime_type:'image/jpeg',size:40*1024*1024}}));
});
test('F8.1 rejects inconsistent identities while immutable historical examples remain accepted',()=>{
  assert.ok(analyzeSchema.safeParse(historical).success);
  const bad=structuredClone(historical);bad.schema_version='F8.1';
  assert.equal(analyzeSchema.safeParse(bad).success,false);
});

test('actual corrected CPU response accepts unavailable calibration and exports dimensions',()=>{
  const response=JSON.parse(readFileSync(new URL('./fixtures/module1-cpu-response.json',import.meta.url),'utf8'));
  assert.ok(analyzeSchema.safeParse(response).success);
  assert.equal(response.summary.review_count,2);
  assert.ok(response.candidates.every(c=>c.classification.reliability===null));
  assert.match(exportCsvText(response,{}),/UNCALIBRATED/);
});
