import type { ReportRequest, ReportResponse } from '../types';
import { requestJson } from './client';
import { reportSchema } from './schema';

export const getReport = (request: ReportRequest, signal?: AbortSignal): Promise<ReportResponse> =>
  requestJson('/report', { method: 'POST', body: JSON.stringify(request), headers: { 'Content-Type': 'application/json' }, schema: reportSchema, signal, timeoutMs: 30000 });
