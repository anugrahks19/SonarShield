import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyGradioError } from '../src/api/gradioError.ts';
import { AnalysisError } from '../src/api/errors.ts';

test('ZeroGPU quota errors get a specific code and do not claim the image was analyzed', () => {
  for (const error of [
    new Error('You have exceeded your ZeroGPU runs limit. Authenticate with a Hugging Face token for more quota.'),
    new AnalysisError('ANALYSIS_FAILED', 'You have exceeded your ZeroGPU runs limit.'),
  ]) {
    const classified = classifyGradioError(error);
    assert.equal(classified.code, 'GPU_QUOTA_EXCEEDED');
    assert.match(classified.message, /Your image was not analyzed/);
  }
});

test('offline and endpoint errors remain distinct from quota exhaustion', () => {
  assert.equal(classifyGradioError(new Error('Failed to fetch')).code, 'API_OFFLINE');
  assert.equal(classifyGradioError(new Error('No endpoint matching "/predict" was found')).code, 'API_ENDPOINT_MISMATCH');
});
