import { useState } from 'react';
import type { AnalyzeResponse } from '../../types';

export default function ReportImage({ analysis, src }: { analysis: AnalyzeResponse; src: string | null }) {
  const [annotated, setAnnotated] = useState(true);
  const width = analysis.input.width;
  const height = analysis.input.height;
  if (!src || !width || !height) return <section className="report-section" id="report-image"><h2>Sonar image</h2><p className="report-muted">Original image unavailable in this browser session. The analysis response contains no image asset.</p></section>;
  return <section className="report-section" id="report-image"><h2>Sonar image</h2><p className="report-muted">Original uploaded image · boxes from F8 detection coordinates</p><div className="report-image-toggle report-no-print"><button type="button" className={!annotated ? 'active' : ''} onClick={() => setAnnotated(false)}>Original</button><button type="button" className={annotated ? 'active' : ''} onClick={() => setAnnotated(true)}>Annotated</button></div><div className="report-image-wrap"><div className="report-image-stage"><img src={src} alt={`${annotated ? 'Annotated' : 'Original'} sonar input ${analysis.input.filename}`} />{annotated && analysis.candidates.map((candidate, index) => {
    const [x1, y1, x2, y2] = candidate.detection.bbox;
    if (![x1, y1, x2, y2].every(Number.isFinite) || x2 <= x1 || y2 <= y1) return null;
    return <div className="report-image-box" key={candidate.candidate_id} style={{ left: `${x1 / width * 100}%`, top: `${y1 / height * 100}%`, width: `${(x2 - x1) / width * 100}%`, height: `${(y2 - y1) / height * 100}%` }}><span>#{String(index + 1).padStart(2, '0')} {candidate.decision.status}</span></div>;
  })}</div></div></section>;
}
