import { describeGradioError } from '../shared/gradio-errors.mjs';

export const SPACE_ID = 'mrintrovert19/sonar-shield-api';
const ENDPOINT = '/analyze_image_gradio';
const MAX_BODY = 8192;

class GatewayError extends Error {
  constructor(code, message, status) { super(message); this.code = code; this.status = status; }
}

export function validateFile(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).some(key => key !== 'file')) throw new GatewayError('INVALID_FILE_REFERENCE', 'Only an uploaded image reference is accepted.', 400);
  const file = body.file;
  if (!file || typeof file !== 'object' || Array.isArray(file) || Object.keys(file).some(key => !['path', 'orig_name', 'mime_type', 'size'].includes(key))) throw new GatewayError('INVALID_FILE_REFERENCE', 'The uploaded image reference is invalid.', 400);
  // Verified against this Space's Gradio upload response; no URL fetching or arbitrary paths.
  if (typeof file.path !== 'string' || file.path.length > 1024 || !/^\/tmp\/gradio\/[a-f0-9]{64}\/[A-Za-z0-9_. -]+\.(?:jpe?g|png)$/i.test(file.path) || file.path.includes('..')) throw new GatewayError('INVALID_FILE_REFERENCE', 'The file must be a JPG or PNG uploaded to the configured Space.', 400);
  if (!['image/jpeg', 'image/png'].includes(file.mime_type) || !Number.isSafeInteger(file.size) || file.size <= 0 || typeof file.orig_name !== 'string' || file.orig_name.length > 255 || /[\x00-\x1f/\\]/.test(file.orig_name)) throw new GatewayError('INVALID_FILE_REFERENCE', 'The image metadata is invalid.', 400);
  return { path: file.path, orig_name: file.orig_name, mime_type: file.mime_type, size: file.size, meta: { _type: 'gradio.FileData' } };
}

function checkOrigin(req, env) {
  const origin = req.headers.origin;
  const site = req.headers['sec-fetch-site'];
  if (typeof origin !== 'string' || (site && site !== 'same-origin')) throw new GatewayError('FORBIDDEN_ORIGIN', 'Live analysis must be requested from this site.', 403);
  let expected;
  if (env.APP_ORIGIN) expected = env.APP_ORIGIN;
  else if (env.VERCEL_URL) expected = `https://${env.VERCEL_URL}`;
  else if (env.NODE_ENV !== 'production') expected = `http://${req.headers.host}`;
  if (!expected || origin !== expected) throw new GatewayError('FORBIDDEN_ORIGIN', 'Live analysis must be requested from this site.', 403);
}

async function readBody(req) {
  if (!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] || '')) throw new GatewayError('INVALID_REQUEST', 'Use an application/json image reference.', 415);
  if (Number(req.headers['content-length']) > MAX_BODY) throw new GatewayError('INVALID_REQUEST', 'Send the image to the Space, not this gateway.', 413);
  if (req.body !== undefined) {
    const serialized = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
    if (Buffer.byteLength(serialized) > MAX_BODY) throw new GatewayError('INVALID_REQUEST', 'The image reference is too large.', 413);
    try { return typeof req.body === 'string' ? JSON.parse(req.body) : req.body; }
    catch { throw new GatewayError('INVALID_REQUEST', 'The request contains invalid JSON.', 400); }
  }
  const chunks = []; let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY) throw new GatewayError('INVALID_REQUEST', 'The image reference is too large.', 413);
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new GatewayError('INVALID_REQUEST', 'The request contains invalid JSON.', 400); }
}

export function createGateway({ connect, env = process.env, timeoutMs = 270000, now = Date.now }) {
  return async function handler(req, res) {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    const send = (status, value) => { if (!res.destroyed && !res.writableEnded) { res.statusCode = status; res.end(JSON.stringify(value)); } };
    if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); send(405, { error: { code: 'METHOD_NOT_ALLOWED', message: 'Use POST for live analysis.' } }); return; }
    let client; let submission; let timer; let detached = false;
    const controller = new AbortController();
    const disconnect = () => { if (!res.writableEnded) controller.abort(new GatewayError('REQUEST_CANCELLED', 'The request was cancelled. GPU time already used may still count.', 499)); };
    const abortFailure = new Promise((_, reject) => controller.signal.addEventListener('abort', () => reject(controller.signal.reason), { once: true }));
    // Mark handled immediately; origin/body rejection can happen before Promise.race.
    abortFailure.catch(() => {});
    res.on('close', disconnect);
    try {
      checkOrigin(req, env);
      const file = validateFile(await readBody(req));
      const token = env.HF_TOKEN?.trim();
      if (!token || !/^hf_[A-Za-z0-9]+$/.test(token)) throw new GatewayError('HF_AUTH_NOT_CONFIGURED', 'Live authentication is not configured. Set HF_TOKEN in Vercel and redeploy; verified examples remain available.', 503);
      const space = env.VITE_GRADIO_SPACE_ID?.trim() || SPACE_ID;
      if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(space)) throw new GatewayError('INVALID_GATEWAY_CONFIG', 'The configured Space identifier is invalid.', 503);
      timer = setTimeout(() => controller.abort(new GatewayError('ANALYSIS_TIMEOUT', 'The live request timed out. It may already have used GPU time; retry manually or open a verified example.', 504)), timeoutMs);
      const run = async () => {
        client = await connect(space, { token, events: ['data', 'status'], record_history: false });
        if (controller.signal.aborted || detached) { client.close(); throw controller.signal.reason; }
        submission = client.submit(ENDPOINT, { image_filepath: file, run_tiled_auxiliary: true });
        let data;
        for await (const event of submission) {
          if (event.type === 'status' && event.stage === 'error') throw event;
          if (event.type === 'data') data = event.data;
          // Non-queued Gradio submissions emit completion without ending their iterator.
          if (event.type === 'status' && event.stage === 'complete') break;
        }
        const output = Array.isArray(data) ? data[0] : undefined;
        const payload = typeof output === 'string' ? JSON.parse(output) : output;
        if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new GatewayError('INVALID_API_RESPONSE', 'The Space returned no valid analysis object.', 502);
        if ('error' in payload) throw payload.error;
        // No credential from an upstream error or response is allowed back to the browser.
        const serialized = JSON.stringify(payload);
        if (serialized.includes(token) || /hf_[A-Za-z0-9]{10,}/.test(serialized)) throw new GatewayError('INVALID_API_RESPONSE', 'The Space returned unsafe response metadata.', 502);
        return payload;
      };
      send(200, await Promise.race([run(), abortFailure]));
    } catch (error) {
      const described = error instanceof GatewayError ? { code: error.code, message: error.message, status: error.status } : describeGradioError(error, { secret: env.HF_TOKEN?.trim(), now: now(), authenticated: true });
      // Log the fixed classification only, never upstream text, headers or credentials.
      if (env.VERCEL) console.warn('Live inference error:', described.code);
      if (described.details?.retryAfterSeconds !== undefined) res.setHeader('Retry-After', String(described.details.retryAfterSeconds));
      send(described.status, { error: described });
    } finally {
      detached = true;
      clearTimeout(timer);
      res.off('close', disconnect);
      if (controller.signal.aborted && submission) {
        // Best effort: do not delay the response indefinitely for cancellation.
        try { Promise.resolve(submission.cancel()).catch(() => {}).finally(() => client?.close()); }
        catch { client?.close(); }
        client?.close();
      } else client?.close();
    }
  };
}
