import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { createGateway, validateFile, SPACE_ID } from '../server/gateway.mjs';
import { describeGradioError } from '../shared/gradio-errors.mjs';

const TOKEN = 'hf_TESTONLYNOTAREALCREDENTIAL';
const ORIGIN = 'https://sonarshield26.vercel.app';
const file = { path: `/tmp/gradio/${'a'.repeat(64)}/sonar.jpg`, orig_name: 'sonar.jpg', mime_type: 'image/jpeg', size: 6 * 1024 * 1024 };
const body = { file };
const output = { status: 'COMPLETED', candidates: [] };

async function invoke({ events = [{ type: 'data', data: [JSON.stringify(output)] }], connectError, request = {}, environment = {}, timeoutMs = 1000, disconnect = false, hang = false } = {}) {
  const req = { method: 'POST', headers: { origin: ORIGIN, host: 'sonarshield26.vercel.app', 'sec-fetch-site': 'same-origin', 'content-type': 'application/json' }, body, ...request };
  const res = new EventEmitter();
  res.headers = {}; res.setHeader = (key, value) => { res.headers[key] = value; };
  res.end = value => { res.text = value; res.writableEnded = true; };
  let calls = 0, closed = 0, cancelled = 0, options, submitted;
  const connect = async (space, opts) => {
    calls++; options = opts; assert.equal(space, SPACE_ID);
    if (connectError) throw connectError;
    return {
      close() { closed++; },
      submit(endpoint, data) {
        submitted = { endpoint, data };
        const iterator = (async function* () {
          if (disconnect) setTimeout(() => res.emit('close'), 1);
          if (hang || disconnect) await new Promise(() => {});
          for (const event of events) yield event;
        })();
        iterator.cancel = async () => { cancelled++; };
        return iterator;
      },
    };
  };
  await createGateway({ connect, env: { HF_TOKEN: TOKEN, APP_ORIGIN: ORIGIN, NODE_ENV: 'production', SONAR_ADMISSION_URL:'https://controller.invalid', SONAR_ADMISSION_TOKEN:'CONTROLLER_TEST_ONLY_01234567890123456789', ...environment }, fetcher:async()=>new Response(JSON.stringify({lease_id:'a'.repeat(32)})), timeoutMs, now: () => Date.parse('2026-10-01T05:00:00Z') })(req, res);
  await new Promise(resolve => setImmediate(resolve));
  return { res, payload: res.text ? JSON.parse(res.text) : null, calls, closed, cancelled, options, submitted };
}

test('authenticated inference uses only a small existing file reference and a fixed endpoint', async () => {
  const result = await invoke();
  assert.equal(result.res.statusCode, 200);
  assert.deepEqual(result.payload, output);
  assert.equal(result.options.token, TOKEN);
  assert.equal(result.options.record_history, false);
  assert.equal(result.submitted.endpoint, '/analyze_image_gradio');
  assert.equal(result.submitted.data.run_tiled_auxiliary, true);
  assert.equal(result.submitted.data.image_filepath.meta._type, 'gradio.FileData');
  assert.equal(result.calls, 1);
  assert.ok(result.closed > 0);
  assert.ok(!result.res.text.includes(TOKEN));
  assert.ok(JSON.stringify(body).length < 1024);
  assert.ok(file.size > 4.5 * 1024 * 1024);
});

test('quota status retains countdown, timestamp and redacts the server credential', async () => {
  const result = await invoke({ events: [{ type: 'status', stage: 'error', original_msg: 'process_completed', message: `You have exceeded your ZeroGPU quota. Try again in 1:23:45. ${TOKEN}` }] });
  assert.equal(result.res.statusCode, 429);
  assert.equal(result.payload.error.code, 'GPU_QUOTA_EXCEEDED');
  assert.match(result.payload.error.message, /authenticated service account/);
  assert.equal(result.payload.error.details.retryAfterSeconds, 5025);
  assert.equal(result.payload.error.details.resetAt, '2026-10-01T06:23:45.000Z');
  assert.equal(result.res.headers['Retry-After'], '5025');
  assert.ok(!result.res.text.includes(TOKEN));
  assert.match(result.payload.error.details.upstreamMessage, /REDACTED/);
  assert.equal(result.calls, 1);
});

test('quota without a countdown never invents a reset time', async () => {
  const result = await invoke({ connectError: new Error('You have exceeded your ZeroGPU runs limit.') });
  assert.equal(result.payload.error.code, 'GPU_QUOTA_EXCEEDED');
  assert.equal(result.payload.error.details.resetAt, undefined);
});

test('authentication, offline, endpoint and malformed response errors stay distinct', async () => {
  for (const [error, code] of [
    [new Error('HTTP 401 invalid token'), 'HF_AUTH_FAILED'],
    [{ error: 'Your token was revoked' }, 'HF_AUTH_FAILED'],
    [new Error('fetch failed'), 'API_OFFLINE'],
    [new Error('No endpoint matching /predict'), 'API_ENDPOINT_MISMATCH'],
  ]) {
    const result = await invoke({ connectError: error });
    assert.equal(result.payload.error.code, code);
  }
  const invalid = await invoke({ events: [{ type: 'data', data: ['{bad json'] }] });
  assert.equal(invalid.payload.error.code, 'INVALID_API_RESPONSE');
  const unsafe = await invoke({ events: [{ type: 'data', data: [{ status: 'COMPLETED', leaked: TOKEN }] }] });
  assert.equal(unsafe.payload.error.code, 'INVALID_API_RESPONSE');
  assert.ok(!unsafe.res.text.includes(TOKEN));
});

test('missing credentials fail without anonymous inference', async () => {
  const result = await invoke({ environment: { HF_TOKEN: '' } });
  assert.equal(result.payload.error.code, 'HF_AUTH_NOT_CONFIGURED');
  assert.equal(result.calls, 0);
});

test('foreign origin, missing origin, arbitrary URLs, traversal and custom endpoints are rejected before inference', async () => {
  for (const origin of ['https://evil.example', undefined]) {
    const result = await invoke({ request: { headers: { origin, 'content-type': 'application/json' } } });
    assert.equal(result.res.statusCode, 403);
    assert.equal(result.calls, 0);
  }
  for (const candidate of [
    { file: { ...file, path: 'https://evil.example/sonar.jpg' } },
    { file: { ...file, path: '/etc/passwd' } },
    { file: { ...file, path: `/tmp/gradio/${'a'.repeat(64)}/../sonar.jpg` } },
    { file: { ...file, url: 'https://evil.example' } },
    { ...body, space: 'other/space' },
    { ...body, endpoint: '/predict' },
  ]) {
    const result = await invoke({ request: { body: candidate } });
    assert.equal(result.res.statusCode, 400);
    assert.equal(result.calls, 0);
  }
  assert.equal(validateFile(body).path, file.path);
});

test('timeout and disconnect attempt cancellation, close the client and never retry', async () => {
  const timeout = await invoke({ hang: true, timeoutMs: 5 });
  assert.equal(timeout.payload.error.code, 'ANALYSIS_TIMEOUT');
  assert.equal(timeout.cancelled, 1);
  assert.equal(timeout.calls, 1);
  const disconnected = await invoke({ disconnect: true });
  assert.equal(disconnected.payload.error.code, 'REQUEST_CANCELLED');
  assert.equal(disconnected.cancelled, 1);
});

test('structured Gradio errors are bounded and duration rejection is not quota exhaustion', () => {
  assert.equal(describeGradioError({ message: 'ZeroGPU illegal duration' }).code, 'GPU_DURATION_REJECTED');
  assert.ok(describeGradioError({ error: 'x'.repeat(9000) }).details.upstreamMessage.length <= 4000);
});
