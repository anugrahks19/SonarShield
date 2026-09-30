import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { REVIEW_STORAGE_KEY, getReviews, saveReview, deleteReview } from '../src/review/reviewStore.ts';

const data = new Map();
globalThis.localStorage = {
  getItem: key => data.get(key) ?? null,
  setItem: (key, value) => data.set(key, String(value)),
};
const outputs = JSON.parse(await readFile(new URL('../../ai/reference/gate_f9_runtime_results.json', import.meta.url), 'utf8'));
const multi = outputs.find(output => output.summary.candidate_count > 1);
const [first, second] = multi.candidates;
const originalDecision = first.decision.status;

test('reviews persist separately per analysis and candidate with exact notes', () => {
  data.clear();
  const reviewA = { analysisId: multi.analysis_id, candidateId: first.candidate_id, status: 'CONFIRMED', note: 'Shadow may be visible.  Keep two spaces.', reviewedAt: '2026-09-30T12:00:00.000Z' };
  const reviewB = { ...reviewA, candidateId: second.candidate_id, status: 'NEEDS_INVESTIGATION', note: 'More adjacent pings needed.' };
  assert.equal(saveReview(reviewA), true);
  assert.equal(saveReview(reviewB), true);
  const restored = getReviews(multi.analysis_id, [first.candidate_id, second.candidate_id]);
  assert.deepEqual(restored[first.candidate_id], reviewA);
  assert.deepEqual(restored[second.candidate_id], reviewB);
  assert.deepEqual(getReviews('ANL-other', [first.candidate_id]), {});
  assert.equal(first.decision.status, originalDecision);
  assert.equal(deleteReview(multi.analysis_id, first.candidate_id), true);
  assert.equal(getReviews(multi.analysis_id, [first.candidate_id])[first.candidate_id], undefined);
  assert.deepEqual(getReviews(multi.analysis_id, [second.candidate_id])[second.candidate_id], reviewB);
});

test('invalid and corrupt local entries are ignored without affecting valid entries', () => {
  data.clear();
  data.set(REVIEW_STORAGE_KEY, '{bad json');
  assert.deepEqual(getReviews(multi.analysis_id, [first.candidate_id]), {});
  assert.equal(saveReview({ analysisId: multi.analysis_id, candidateId: first.candidate_id, status: 'UNKNOWN', note: '', reviewedAt: new Date().toISOString() }), false);
  const good = { analysisId: multi.analysis_id, candidateId: first.candidate_id, status: 'FALSE_POSITIVE', note: '', reviewedAt: new Date().toISOString() };
  assert.equal(saveReview(good), true);
  const stored = JSON.parse(data.get(REVIEW_STORAGE_KEY));
  stored.reviews['["wrong","key"]'] = { ...good, status: 'CONFIRMED' };
  stored.reviews['["invalid","status"]'] = { ...good, status: 'REVIEW' };
  data.set(REVIEW_STORAGE_KEY, JSON.stringify(stored));
  assert.deepEqual(getReviews(multi.analysis_id, [first.candidate_id]), { [first.candidate_id]: good });
});
