import { acquireSupabaseAdmission } from './supabase.mjs';
// Authenticated, durable controller; no in-memory serverless quota counters.
export async function acquireAdmission(env, fetcher = fetch) {
  if (env.SONAR_ADMISSION_PROVIDER === 'supabase') return acquireSupabaseAdmission(env,fetcher);
  if (env.SONAR_ADMISSION_PROVIDER && env.SONAR_ADMISSION_PROVIDER !== 'sqlite') throw failure('LIVE_LIMITER_UNAVAILABLE','Unknown live usage controller.',503);
  const url = env.SONAR_ADMISSION_URL;
  const token = env.SONAR_ADMISSION_TOKEN;
  if (!url && !token) return null; // Explicitly unprotected legacy deployment.
  let parsed;
  try { parsed = new URL(url); } catch { throw failure('LIVE_LIMITER_UNAVAILABLE', 'Live usage control is not configured correctly.', 503); }
  if (parsed.username || parsed.password || parsed.search || parsed.hash || (parsed.protocol !== 'https:' && !(env.NODE_ENV !== 'production' && parsed.protocol === 'http:' && ['localhost','127.0.0.1'].includes(parsed.hostname))) || typeof token !== 'string' || token.length < 32) throw failure('LIVE_LIMITER_UNAVAILABLE', 'Live usage control is not configured correctly.', 503);
  const base = parsed.href.replace(/\/$/, '');
  let response;
  try {
    response = await fetcher(`${base}/admission/acquire`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(5000), redirect: 'error' });
  } catch { throw failure('LIVE_LIMITER_UNAVAILABLE', 'Live usage control is unavailable. No inference was started; verified examples remain available.', 503); }
  if (response.status === 429) throw failure('LIVE_USAGE_LIMIT', 'The site live-run budget or concurrency limit was reached. No inference started. Try manually later or open a verified example.', 429);
  if (!response.ok) throw failure('LIVE_LIMITER_UNAVAILABLE', 'Live usage control failed. No inference was started.', 503);
  let lease;
  try { lease = await response.json(); } catch { throw failure('LIVE_LIMITER_UNAVAILABLE', 'Live usage control returned invalid data.', 503); }
  if (!/^[a-f0-9]{32}$/.test(lease?.lease_id)) throw failure('LIVE_LIMITER_UNAVAILABLE', 'Live usage control returned invalid data.', 503);
  return { release: async () => {
    try { await fetcher(`${base}/admission/release`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ lease_id: lease.lease_id }), signal: AbortSignal.timeout(3000), redirect: 'error' }); } catch { /* Expiring lease keeps failure conservative. */ }
  } };
}
function failure(code, message, status) { return Object.assign(new Error(message), { admissionError: true, code, status }); }
