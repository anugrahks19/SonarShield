import type { AnalyzeResponse } from '../types';
import type { HumanReview } from '../review/reviewStore';
import { locationState } from '../components/map/mapData.ts';

export type ResultSource = 'LIVE_ANALYSIS' | 'PRECOMPUTED_EXAMPLE';
const sourceLabel = (source: ResultSource) => source === 'PRECOMPUTED_EXAMPLE' ? 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE' : 'LIVE ANALYSIS';

export const safeAnalysisName = (analysisId: string) => {
  const cleaned = analysisId.replace(/[^A-Za-z0-9._-]/g, '_').replace(/^\.+/, '').slice(0, 80);
  return `sonar-shield-${cleaned || 'analysis'}`;
};

export function exportJsonText(analysis: AnalyzeResponse, reviews: Record<string, HumanReview>, source: ResultSource = 'LIVE_ANALYSIS'): string {
  const humanReview = analysis.candidates.flatMap(candidate => {
    const review = reviews[candidate.candidate_id];
    return review && review.analysisId === analysis.analysis_id ? [review] : [];
  });
  return JSON.stringify({ result_source: source, source_label: sourceLabel(source), source_note: source === 'PRECOMPUTED_EXAMPLE' ? 'Previously completed F9 analysis; no inference ran for this session.' : 'Live Space response for this session.', analysis, human_review: { storage: 'LOCAL_BROWSER', reviews: humanReview } }, null, 2);
}

const csvCell = (value: string | number | null | undefined) => {
  if (value === null || value === undefined) return '';
  const text = String(value);
  // A spreadsheet may treat leading formula characters as executable cells.
  const safe = /^[=+@-]/.test(text) && typeof value === 'string' ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
};

export function exportCsvText(analysis: AnalyzeResponse, reviews: Record<string, HumanReview>, source: ResultSource = 'LIVE_ANALYSIS'): string {
  const header = ['analysis_id', 'candidate_id', 'class', 'ai_decision', 'fusion_score', 'ai_confidence', 'source_mode', 'localization_status', 'latitude', 'longitude', 'human_review_status', 'reviewed_at', 'result_source', 'source_label'];
  const rows = analysis.candidates.map(candidate => {
    const geo = locationState(candidate) === 'GEOGRAPHIC' ? candidate.localization.coordinates.geographic : null;
    const review = reviews[candidate.candidate_id]?.analysisId === analysis.analysis_id ? reviews[candidate.candidate_id] : undefined;
    return [analysis.analysis_id, candidate.candidate_id, candidate.detection.class_name, candidate.decision.status,
      candidate.decision.fusion_score, candidate.detection.confidence, candidate.detection.source_mode,
      candidate.localization.metadata.status, geo?.latitude, geo?.longitude, review?.status ?? 'NOT_REVIEWED', review?.reviewedAt, source, sourceLabel(source)]
      .map(csvCell).join(',');
  });
  return [header.join(','), ...rows].join('\r\n') + '\r\n';
}

export function downloadText(name: string, contents: string, mime: string) {
  const url = URL.createObjectURL(new Blob([contents], { type: mime }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
