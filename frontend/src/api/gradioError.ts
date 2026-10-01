import { AnalysisError } from './errors.ts';
import { describeGradioError } from '../../shared/gradio-errors.mjs';

export function classifyGradioError(error: unknown): AnalysisError {
  if (error instanceof AnalysisError && error.code !== 'ANALYSIS_FAILED') return error;
  const described = describeGradioError(error);
  return new AnalysisError(described.code, described.message, described.details, described.status);
}
