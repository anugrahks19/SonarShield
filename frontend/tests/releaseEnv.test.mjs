import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

const check = (overrides) => {
  const env = { ...process.env, VITE_API_BASE_URL: '', VITE_DEMO_MODE: 'false', VITE_USE_MOCK_DATA: 'false', ...overrides };
  return spawnSync(process.execPath, ['scripts/verify-release-env.mjs'], { cwd: new URL('..', import.meta.url), env, encoding: 'utf8' });
};

test('release build requires a deployed F8 HTTPS origin', () => {
  assert.notEqual(check({}).status, 0);
  assert.notEqual(check({ VITE_API_BASE_URL: 'http://127.0.0.1:8000' }).status, 0);
  assert.notEqual(check({ VITE_API_BASE_URL: 'https://user:secret@api.example.test/' }).status, 0);
  assert.equal(check({ VITE_API_BASE_URL: 'https://api.example.test' }).status, 0);
});

test('release build rejects explicit demo and mock modes', () => {
  assert.notEqual(check({ VITE_API_BASE_URL: 'https://api.example.test', VITE_DEMO_MODE: 'true' }).status, 0);
  assert.notEqual(check({ VITE_API_BASE_URL: 'https://api.example.test', VITE_USE_MOCK_DATA: 'true' }).status, 0);
});
