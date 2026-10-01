import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once, EventEmitter } from 'node:events';
import { Client } from '@gradio/client';
import { createGateway } from '../server/gateway.mjs';

test('the pinned Gradio client sends the server token on inference and never reuploads the reference', async () => {
  const token = 'hf_TESTONLYNOTAREALCREDENTIAL';
  const requests = [];
  let root;
  const server = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    requests.push({ path: req.url, auth: req.headers.authorization, body: Buffer.concat(chunks).toString() });
    res.setHeader('Content-Type', 'application/json');
    if (req.url === '/config') res.end(JSON.stringify({
      root, api_prefix: '/gradio_api', protocol: 'sse', enable_queue: false, run_history: false,
      components: [{ id: 1, type: 'image', props: {} }, { id: 2, type: 'checkbox', props: {} }, { id: 3, type: 'json', props: {} }],
      dependencies: [{ id: 0, api_name: 'analyze_image_gradio', inputs: [1, 2], outputs: [3], queue: false, api_visibility: 'public', types: { generator: false } }],
    }));
    else if (req.url === '/gradio_api/info') res.end(JSON.stringify({ named_endpoints: { '/analyze_image_gradio': {
      parameters: [
        { parameter_name: 'image_filepath', parameter_has_default: false, component: 'Image', type: { type: 'string' } },
        { parameter_name: 'run_tiled_auxiliary', parameter_has_default: true, parameter_default: true, component: 'Checkbox', type: { type: 'boolean' } },
      ], returns: [{ component: 'JSON', type: { type: 'object' } }],
    } }, unnamed_endpoints: {} }));
    else if (req.url === '/gradio_api/run/analyze_image_gradio') res.end(JSON.stringify({ data: [{ status: 'COMPLETED', candidates: [] }] }));
    else { res.statusCode = 404; res.end('{}'); }
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  root = `http://127.0.0.1:${server.address().port}`;
  try {
    const response = new EventEmitter();
    response.setHeader = () => {};
    response.end = text => { response.text = text; response.writableEnded = true; };
    const handler = createGateway({
      connect: (_, options) => Client.connect(root, options),
      env: { HF_TOKEN: token, APP_ORIGIN: 'https://sonarshield26.vercel.app' }, timeoutMs: 5000,
    });
    await handler({ method: 'POST', headers: { origin: 'https://sonarshield26.vercel.app', 'content-type': 'application/json' }, body: {
      file: { path: `/tmp/gradio/${'a'.repeat(64)}/sonar.jpg`, orig_name: 'sonar.jpg', mime_type: 'image/jpeg', size: 1234 },
    } }, response);
    assert.equal(response.statusCode, 200, response.text + ' requests=' + JSON.stringify(requests.map(request => request.path)));
    const inference = requests.filter(request => request.path.includes('/run/'));
    assert.equal(inference.length, 1);
    assert.equal(inference[0].auth, `Bearer ${token}`);
    assert.equal(JSON.parse(inference[0].body).data[0].path, `/tmp/gradio/${'a'.repeat(64)}/sonar.jpg`);
    assert.equal(requests.filter(request => request.path.includes('/upload')).length, 0);
    assert.ok(!response.text.includes(token));
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});
