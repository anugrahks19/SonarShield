const MAX_MESSAGE = 4000;

export function safeMessage(value, secret = '', depth = 0) {
  if (depth > 4) return '';
  let message = '';
  if (typeof value === 'string') message = value;
  else if (value instanceof Error) message = value.message;
  else if (Array.isArray(value)) message = value.slice(0, 8).map(item => safeMessage(item, secret, depth + 1)).join('; ');
  else if (value && typeof value === 'object') {
    message = safeMessage(value.message || value.error || value.detail || value.original_msg || '', secret, depth + 1);
  }
  if (secret) message = message.split(secret).join('[REDACTED]');
  return message.replace(/hf_[A-Za-z0-9_-]+/g, '[REDACTED]')
    .replace(/Bearer\s+[^\s"'<>]+/gi, 'Bearer [REDACTED]').slice(0, MAX_MESSAGE);
}

export function describeGradioError(error, { secret = '', now = Date.now(), authenticated = false } = {}) {
  const original = safeMessage(error, secret) || 'The Space analysis request failed.';
  const details = { upstreamMessage: original, receivedAt: new Date(now).toISOString() };
  if (/ZeroGPU.*illegal duration|illegal duration.*ZeroGPU/i.test(original)) {
    return { code: 'GPU_DURATION_REJECTED', message: 'Hugging Face rejected the requested GPU duration. Waiting for a quota reset may not resolve this.', details, status: 503 };
  }
  if (/ZeroGPU.*(?:limit|quota)|(?:limit|quota).*ZeroGPU/i.test(original)) {
    const countdown = original.match(/(?:try again|retry|reset(?:s)?)\s*(?:in|after)?\s*[:=]?\s*(\d{1,3}):(\d{2}):(\d{2})/i);
    if (countdown && Number(countdown[2]) < 60 && Number(countdown[3]) < 60) {
      details.retryAfterSeconds = Number(countdown[1]) * 3600 + Number(countdown[2]) * 60 + Number(countdown[3]);
      details.resetAt = new Date(now + details.retryAfterSeconds * 1000).toISOString();
    }
    return { code: 'GPU_QUOTA_EXCEEDED',
      message: `Live inference is unavailable because ${authenticated ? 'the authenticated service account reached its ZeroGPU limit' : 'Hugging Face rejected this request for a ZeroGPU limit'}. Your image was not analyzed. Try again later or open a verified example.`,
      details, status: 429 };
  }
  if (/\b(?:401|403)\b|unauthori[sz]ed|invalid.{0,20}token|token.{0,20}(?:invalid|revoked)|authentication|forbidden/i.test(original)) {
    return { code: 'HF_AUTH_FAILED', message: 'Hugging Face authentication failed. The service token needs checking in Vercel.', details, status: 502 };
  }
  if (/No endpoint matching/i.test(original)) return { code: 'API_ENDPOINT_MISMATCH', message: 'The Space analysis endpoint could not be found.', details, status: 502 };
  if (error instanceof SyntaxError) return { code: 'INVALID_API_RESPONSE', message: 'The Space returned invalid JSON.', details, status: 502 };
  if (/Space metadata could not be loaded|Failed to fetch|fetch failed|could not resolve app config|network|connection|\b(?:502|503|504)\b/i.test(original)) {
    return { code: 'API_OFFLINE', message: 'The Hugging Face Space could not be reached. Your image was not analyzed.', details, status: 502 };
  }
  return { code: 'ANALYSIS_FAILED', message: 'The Space analysis request failed. See Technical details.', details, status: 502 };
}
