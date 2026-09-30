import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { analyzeSchema, detectSchema, healthSchema, reportSchema } from '../src/api/schema.ts';
import { responseError } from '../src/api/errors.ts';

const outputs = JSON.parse(await readFile(new URL('../../ai/reference/gate_f9_runtime_results.json', import.meta.url), 'utf8'));

test('all ten frozen F9 runtime responses validate without changing decisions or boxes', () => {
  assert.equal(outputs.length, 10);
  for (const output of outputs) {
    const parsed = analyzeSchema.safeParse(output);
    assert.ok(parsed.success, `${output.input.filename}: ${parsed.success ? '' : JSON.stringify(parsed.error.issues.slice(0, 3))}`);
    assert.equal(parsed.data.candidates.length, output.summary.candidate_count);
    for (let i = 0; i < output.candidates.length; i++) {
      assert.equal(parsed.data.candidates[i].decision.status, output.candidates[i].decision.status);
      assert.equal(parsed.data.candidates[i].decision.fusion_score, output.candidates[i].decision.fusion_score);
      assert.deepEqual(parsed.data.candidates[i].detection.bbox, output.candidates[i].detection.bbox);
    }
  }
});

test('frozen examples include zero, single, and multiple candidate responses', () => {
  const counts = outputs.map(output => output.summary.candidate_count);
  assert.ok(counts.includes(0)); assert.ok(counts.includes(1)); assert.ok(counts.includes(2));
  const contact105 = outputs.find(output => output.input.filename.startsWith('Contact_105'));
  assert.deepEqual(contact105.candidates.map(candidate => candidate.detection.source_mode), ['GLOBAL', 'TILED']);
});

test('health, raw detect, and report response shapes match F8 schemas', () => {
  assert.ok(healthSchema.safeParse({ status: 'OK', schema_version: 'F8.0', components: { detector: 'READY', fusion: 'READY', decision_policy: 'READY', calibration: 'READY', unknown_detector: 'READY' }, pipeline_version: 'v1.2', uptime_seconds: 1 }).success);
  assert.ok(detectSchema.safeParse({ schema_version: 'F8.0', analysis_id: 'ANL-test', status: 'COMPLETED', input: { input_id: 'IMG-test', filename: 'test.jpg', sha256: 'hash', width: 640, height: 640 }, summary: { raw_candidate_count: 0 }, raw_candidates: [], processing: { pipeline_version: 'v1.2', processing_time_ms: 1 } }).success);
  assert.ok(reportSchema.safeParse({ schema_version: 'F8.0', report_id: 'RPT-test', status: 'GENERATED', report_url: '/static/report.json', download_url: null, data: null }).success);
});

test('F8 and FastAPI errors keep backend codes and present validation failures safely', () => {
  const f8 = responseError(500, { schema_version: 'F8.0', error: { code: 'MODEL_UNAVAILABLE', message: 'Detector unavailable', details: { component: 'detector' } }, request_id: 'req' });
  assert.equal(f8.code, 'MODEL_UNAVAILABLE'); assert.equal(f8.message, 'Detector unavailable');
  const notFound = responseError(404, { detail: { code: 'REPORT_NOT_FOUND', message: 'Analysis ID not found' } });
  assert.equal(notFound.code, 'REPORT_NOT_FOUND');
  const invalid = responseError(422, { detail: [{ loc: ['body', 'file'], msg: 'Field required' }] });
  assert.equal(invalid.code, 'HTTP_422'); assert.match(invalid.message, /rejected/);
});

test('malformed analysis payload is rejected', () => {
  const malformed = { ...outputs[0], candidates: [{ ...outputs[0].candidates[0], decision: { ...outputs[0].candidates[0].decision, status: null } }] };
  assert.equal(analyzeSchema.safeParse(malformed).success, false);
});
