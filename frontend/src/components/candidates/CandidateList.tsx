import { memo, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { Candidate, DecisionStatus } from '../../types';
import type { HumanReview, HumanReviewStatus } from '../../review/reviewStore';
import ReviewStatusBadge from '../review/ReviewStatusBadge';
import { DecisionBadge, format } from '../ui/Display';
import { locationState } from '../map/mapData';

const aiFilters: Array<'ALL' | DecisionStatus> = ['ALL', 'CONFIRM', 'REVIEW', 'REJECT', 'UNKNOWN'];
const humanFilters: Array<'ALL' | HumanReviewStatus> = ['ALL', 'NOT_REVIEWED', 'CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_INVESTIGATION'];
type Props = { candidates: Candidate[]; selectedId: string | null; onSelect: (id: string) => void; hasAnalysis: boolean; reviews: Record<string, HumanReview> };

function CandidateList({ candidates, selectedId, onSelect, hasAnalysis, reviews }: Props) {
  const [aiFilter, setAiFilter] = useState<(typeof aiFilters)[number]>('ALL');
  const [humanFilter, setHumanFilter] = useState<(typeof humanFilters)[number]>('ALL');
  const rows = useRef<(HTMLTableRowElement | null)[]>([]);
  const visible = candidates.filter(candidate =>
    (aiFilter === 'ALL' || candidate.decision.status === aiFilter)
    && (humanFilter === 'ALL' || (reviews[candidate.candidate_id]?.status ?? 'NOT_REVIEWED') === humanFilter));
  const onRowKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, candidate: Candidate, row: number) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(candidate.candidate_id); }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const next = Math.max(0, Math.min(visible.length - 1, row + (event.key === 'ArrowDown' ? 1 : -1)));
      rows.current[next]?.focus();
      onSelect(visible[next].candidate_id);
    }
  };
  return <section className="candidate-list panel" id="candidates"><div className="panel-heading"><div><span className="eyebrow">REVIEW QUEUE · BACKEND ORDER</span><h2>Candidates <em>{candidates.length}</em></h2></div></div>
    <div className="review-filters"><div><span>AI DECISION</span><div className="filters" role="group" aria-label="Filter AI decisions">{aiFilters.map(value => <button type="button" key={value} className={aiFilter === value ? 'active' : ''} aria-pressed={aiFilter === value} onClick={() => setAiFilter(value)}>{value}</button>)}</div></div><div><span>HUMAN REVIEW</span><div className="filters" role="group" aria-label="Filter human reviews">{humanFilters.map(value => <button type="button" key={value} className={humanFilter === value ? 'active' : ''} aria-pressed={humanFilter === value} onClick={() => setHumanFilter(value)}>{value.replaceAll('_', ' ')}</button>)}</div></div></div>
    {candidates.length ? <div className="table-wrap"><table><thead><tr><th># / ID</th><th>Class</th><th>AI Decision</th><th>Fusion</th><th>Source</th><th>Location</th><th>Human Review</th></tr></thead><tbody>{visible.map((candidate, row) => { const index = candidates.indexOf(candidate); const humanStatus = reviews[candidate.candidate_id]?.status ?? 'NOT_REVIEWED'; const location = locationState(candidate); return <tr key={candidate.candidate_id} ref={node => { rows.current[row] = node; }} tabIndex={0} aria-label={`Candidate ${index + 1}, ${candidate.detection.class_name}, AI ${candidate.decision.status}, location ${location}, human ${humanStatus}`} aria-selected={selectedId === candidate.candidate_id} className={selectedId === candidate.candidate_id ? 'selected' : ''} onClick={() => onSelect(candidate.candidate_id)} onKeyDown={event => onRowKeyDown(event, candidate, row)}><td className="mono"><strong>#{String(index + 1).padStart(2, '0')}</strong><small>{candidate.candidate_id}</small></td><td>{candidate.detection.class_name}</td><td><DecisionBadge status={candidate.decision.status} /></td><td className="mono">{format(candidate.decision.fusion_score)}</td><td className="mono muted">{candidate.detection.source_mode}</td><td><span className={`geo-row-label ${location === 'PIXEL_ONLY' ? 'pixel' : location === 'INVALID' ? 'invalid' : ''}`}>{location === 'GEOGRAPHIC' ? 'GEO' : location === 'PIXEL_ONLY' ? 'PIXEL ONLY' : location.replaceAll('_', ' ')}</span></td><td><ReviewStatusBadge status={humanStatus} /></td></tr>; })}</tbody></table>{visible.length === 0 && <p className="empty-note">No candidates match these filters.</p>}</div> : <p className="empty-note">{hasAnalysis ? 'No candidates returned by the analysis pipeline.' : 'Analyze a sonar image to populate this result strip.'}</p>}
  </section>;
}

export default memo(CandidateList);
