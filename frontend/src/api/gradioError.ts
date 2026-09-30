import { AnalysisError } from './errors.ts';

export function classifyGradioError(error: unknown): AnalysisError {
  const message = error instanceof Error ? error.message : 'The Space analysis request failed.';
  if (/ZeroGPU.*(?:limit|quota)|(?:limit|quota).*ZeroGPU/i.test(message)) {
    return new AnalysisError('GPU_QUOTA_EXCEEDED', 'Live inference is unavailable because the shared ZeroGPU limit was reached. Your image was not analyzed. Try again later or open a verified example.');
  }
  if (error instanceof AnalysisError) return error;
  if (error instanceof SyntaxError) return new AnalysisError('INVALID_API_RESPONSE', 'The Space returned invalid JSON.');
  if (message.includes('No endpoint matching')) return new AnalysisError('API_ENDPOINT_MISMATCH', message);
  if (message.includes('Space metadata could not be loaded') || message.includes('Failed to fetch')) {
    return new AnalysisError('API_OFFLINE', 'The Hugging Face Space could not be reached. Your image was not analyzed.');
  }
  return new AnalysisError('ANALYSIS_FAILED', message);
}
