export class AnalysisError extends Error {
  code: string;
  details?: Record<string, unknown>;
  status?: number;
  constructor(code: string, message: string, details?: Record<string, unknown>, status?: number) {
    super(message); this.name = 'AnalysisError'; this.code = code; this.details = details; this.status = status;
  }
}

type ErrorBody = { error?: { code?: unknown; message?: unknown; details?: unknown }; detail?: unknown };

export function responseError(status: number, body: unknown): AnalysisError {
  const data = body && typeof body === 'object' ? body as ErrorBody : {};
  const detail = data.error ?? data.detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const value = detail as Record<string, unknown>;
    if (typeof value.code === 'string' && typeof value.message === 'string') {
      return new AnalysisError(value.code, value.message, typeof value.details === 'object' && value.details !== null ? value.details as Record<string, unknown> : undefined, status);
    }
  }
  if (status === 422) return new AnalysisError('HTTP_422', 'The analysis service rejected the request. Check the selected file.', { validation: detail }, status);
  if (status === 404) return new AnalysisError('HTTP_404', 'The requested analysis resource was not found.', undefined, status);
  if (status >= 500) return new AnalysisError(`HTTP_${status}`, 'The analysis service encountered an error. Please retry.', undefined, status);
  return new AnalysisError(`HTTP_${status}`, typeof detail === 'string' ? detail : `The service returned HTTP ${status}.`, undefined, status);
}
