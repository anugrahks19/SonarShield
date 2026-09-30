import type { ReportRequest, ReportResponse } from '../types';

export const getReport = async (_request: ReportRequest, _signal?: AbortSignal): Promise<ReportResponse> => {
  return {
    schema_version: "F7.0",
    report_id: `RPT-${Math.random().toString(36).substring(7)}`,
    status: "GENERATED",
    report_url: null,
    download_url: null,
    data: null
  };
};
