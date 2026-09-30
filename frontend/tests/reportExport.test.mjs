import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { exportJsonText, exportCsvText, safeAnalysisName } from '../src/reports/export.ts';

const outputs = JSON.parse(await readFile(new URL('../../ai/reference/gate_f9_runtime_results.json', import.meta.url), 'utf8'));
const multiple = outputs.find(output => output.summary.candidate_count === 2);
const zero = outputs.find(output => output.summary.candidate_count === 0);

test('JSON export preserves the F8 object and separates local human review', () => {
  const source = structuredClone(multiple);
  const first = source.candidates[0];
  const review = { analysisId: source.analysis_id, candidateId: first.candidate_id, status: 'CONFIRMED', note: 'Exact note, with comma and "quotes".', reviewedAt: '2026-09-30T12:00:00.000Z' };
  const json = JSON.parse(exportJsonText(source, { [first.candidate_id]: review }));
  assert.deepEqual(json.analysis, source);
  assert.equal(json.result_source, 'LIVE_ANALYSIS');
  assert.deepEqual(json.human_review.reviews, [review]);
  assert.equal(json.human_review.storage, 'LOCAL_BROWSER');
  assert.equal(first.decision.status, source.candidates[0].decision.status);
  assert.equal(json.analysis.candidates[0].decision.status, first.decision.status);
});

test('CSV keeps backend values, separate review state, and blank missing coordinates', () => {
  const first = multiple.candidates[0];
  const review = { analysisId: multiple.analysis_id, candidateId: first.candidate_id, status: 'FALSE_POSITIVE', note: 'local only', reviewedAt: '2026-09-30T12:00:00.000Z' };
  const lines = exportCsvText(multiple, { [first.candidate_id]: review }).trim().split('\r\n');
  assert.equal(lines.length, 3);
  assert.match(lines[0], /ai_decision.*human_review_status/);
  assert.ok(lines[1].includes(`"${first.decision.status}"`));
  assert.ok(lines[1].includes(`"${first.decision.fusion_score}"`));
  assert.ok(lines[1].includes(',,,"FALSE_POSITIVE"'));
  assert.ok(lines[2].includes(',,,"NOT_REVIEWED"'));
  assert.equal(exportCsvText(zero, {}).trim().split('\r\n').length, 1);
  assert.match(lines[0], /result_source,source_label$/);
  assert.match(lines[1], /"LIVE_ANALYSIS","LIVE ANALYSIS"$/);
});

test('precomputed exports disclose their source without altering analysis', () => {
  const json = JSON.parse(exportJsonText(multiple, {}, 'PRECOMPUTED_EXAMPLE'));
  assert.equal(json.result_source, 'PRECOMPUTED_EXAMPLE');
  assert.equal(json.source_label, 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE');
  assert.match(json.source_note, /no inference ran/i);
  assert.deepEqual(json.analysis, multiple);
  assert.match(exportCsvText(multiple, {}, 'PRECOMPUTED_EXAMPLE'), /"PRECOMPUTED_EXAMPLE","PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE"/);
});

test('geographic CSV exports supplied coordinates without rounding', () => {
  const source = structuredClone(multiple);
  source.candidates[0].localization.metadata.status = 'GEOGRAPHIC';
  source.candidates[0].localization.coordinates.geographic = { coordinate_system: 'WGS84', latitude: 10.123456789, longitude: 76.987654321, heading_deg: null };
  const csv = exportCsvText(source, {});
  assert.match(csv, /"10\.123456789","76\.987654321"/);
  assert.ok(!csv.includes('"0","0"'));
});

test('analysis IDs cannot escape safe export filenames', () => {
  assert.equal(safeAnalysisName('../ANL\\secret/?*'), 'sonar-shield-_ANL_secret___');
  assert.equal(safeAnalysisName(''), 'sonar-shield-analysis');
});
