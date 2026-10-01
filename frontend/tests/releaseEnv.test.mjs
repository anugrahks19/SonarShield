import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

const check = (overrides) => {
  const env = { ...process.env, VITE_GRADIO_SPACE_ID: 'mrintrovert19/sonar-shield-api', VITE_DEMO_MODE: 'false', VITE_USE_MOCK_DATA: 'false', ...overrides };
  return spawnSync(process.execPath, ['scripts/verify-release-env.mjs'], { cwd: new URL('..', import.meta.url), env, encoding: 'utf8' });
};

test('release build requires a valid Hugging Face Space identifier', () => {
  assert.notEqual(check({ VITE_GRADIO_SPACE_ID: 'http://127.0.0.1:8000' }).status, 0);
  assert.notEqual(check({ VITE_GRADIO_SPACE_ID: 'https://user:secret@api.example.test/' }).status, 0);
  assert.equal(check({ VITE_GRADIO_SPACE_ID: 'mrintrovert19/sonar-shield-api' }).status, 0);
});

test('release build rejects explicit demo and mock modes', () => {
  assert.notEqual(check({ VITE_GRADIO_SPACE_ID: 'mrintrovert19/sonar-shield-api', VITE_DEMO_MODE: 'true' }).status, 0);
  assert.notEqual(check({ VITE_GRADIO_SPACE_ID: 'mrintrovert19/sonar-shield-api', VITE_USE_MOCK_DATA: 'true' }).status, 0);
});

test('release build rejects public HF credentials without echoing their values', () => {
  const token = 'hf_TESTONLYNOTAREALCREDENTIAL';
  const result = check({ VITE_HF_TOKEN: token });
  assert.notEqual(result.status, 0);
  assert.ok(!result.stderr.includes(token));
  assert.equal(check({ HF_TOKEN: token }).status, 0);
});
