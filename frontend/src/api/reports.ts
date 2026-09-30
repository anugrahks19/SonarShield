import type { ReportRequest, ReportResponse } from '../types';
import { AnalysisError } from './errors';

export const getReport = async (_request: ReportRequest, _signal?: AbortSignal): Promise<ReportResponse> => {
  void _request; void _signal;
  throw new AnalysisError('ENDPOINT_UNAVAILABLE', 'The deployed Gradio Space has no report endpoint. Use the current analysis JSON, CSV, or browser print export.');
};
