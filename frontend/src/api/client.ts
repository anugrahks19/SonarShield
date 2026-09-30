import type { z } from 'zod';
import { apiBaseUrl } from '../config/env';
import { AnalysisError, responseError } from './errors';

export type RequestOptions<T> = { method?: 'GET' | 'POST'; body?: BodyInit; schema: z.ZodType<T>; signal?: AbortSignal; timeoutMs?: number; headers?: HeadersInit };

export async function requestJson<T>(path: string, options: RequestOptions<T>): Promise<T> {
  if (apiBaseUrl === null) throw new AnalysisError('API_CONFIG_MISSING', 'The F8 API URL is not configured for this deployment.');
  const controller = new AbortController();
  let timedOut = false;
  const cancel = () => controller.abort();
  options.signal?.addEventListener('abort', cancel, { once: true });
  if (options.signal?.aborted) controller.abort();
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, options.timeoutMs ?? 30000);
  try {
    let response: Response;
    try {
      response = await fetch(`${apiBaseUrl}${path}`, { method: options.method ?? 'GET', body: options.body, headers: options.headers, signal: controller.signal });
    } catch {
      if (timedOut) throw new AnalysisError('API_TIMEOUT', 'The analysis service did not respond in time. Please retry.');
      if (controller.signal.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.');
      throw new AnalysisError('API_OFFLINE', 'The SONAR-SHIELD analysis service could not be reached.');
    }
    let payload: unknown;
    try { payload = await response.json(); }
    catch {
      if (!response.ok) throw responseError(response.status, null);
      throw new AnalysisError('INVALID_API_RESPONSE', 'The analysis service returned a response that was not valid JSON.', { path });
    }
    if (!response.ok) throw responseError(response.status, payload);
    const parsed = options.schema.safeParse(payload);
    if (!parsed.success) {
      throw new AnalysisError('INVALID_API_RESPONSE', 'The analysis service returned an unexpected response.', {
        path,
        issues: parsed.error.issues.slice(0, 12).map(issue => ({ path: issue.path.join('.'), message: issue.message })),
      }, response.status);
    }
    return parsed.data;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', cancel);
  }
}
