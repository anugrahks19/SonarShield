import type { Candidate } from '../../types';
import type { HumanReview } from '../../review/reviewStore';

type Props = { candidates: Candidate[]; reviews: Record<string, HumanReview>; selectedId: string | null; onSelect: (id: string) => void };

export default function ReviewSummary({ candidates, reviews, selectedId, onSelect }: Props) {
  const reviewed = candidates.filter(candidate => Boolean(reviews[candidate.candidate_id])).length;
  const pending = candidates.length - reviewed;
  const confirmed = candidates.filter(candidate => reviews[candidate.candidate_id]?.status === 'CONFIRMED').length;
  const falsePositive = candidates.filter(candidate => reviews[candidate.candidate_id]?.status === 'FALSE_POSITIVE').length;
  const needsInvestigation = candidates.filter(candidate => reviews[candidate.candidate_id]?.status === 'NEEDS_INVESTIGATION').length;
  const current = candidates.findIndex(candidate => candidate.candidate_id === selectedId);
  const nextUnreviewed = [...candidates.slice(current + 1), ...candidates.slice(0, current + 1)]
    .find(candidate => !reviews[candidate.candidate_id]);
  const navigate = (offset: number) => {
    const candidate = candidates[current + offset];
    if (candidate) onSelect(candidate.candidate_id);
  };
  return <section className="review-summary panel" aria-label="Human review queue">
    <div className="review-summary-head"><div><span className="eyebrow">HUMAN REVIEW QUEUE</span><h2>Review progress</h2></div><span className="local-review-tag" title="Human review is stored in this browser because F8 has no review persistence endpoint.">LOCAL REVIEW STATE</span></div>
    {candidates.length === 0 ? <p className="empty-note">NO CANDIDATES TO REVIEW</p> : <>
      <div className="review-progress-line"><strong>{reviewed} / {candidates.length} REVIEWED</strong><span>{pending === 0 ? `REVIEW COMPLETE · All ${candidates.length} candidates have a human assessment.` : `${pending} pending human assessment${pending === 1 ? '' : 's'}`}</span></div>
      <progress max={candidates.length} value={reviewed} aria-label="Human review completion" />
      <div className="review-counts"><span><b>{candidates.length}</b> TOTAL</span><span><b>{pending}</b> NOT REVIEWED</span><span><b>{confirmed}</b> CONFIRMED</span><span><b>{falsePositive}</b> FALSE POSITIVES</span><span><b>{needsInvestigation}</b> NEEDS INVESTIGATION</span></div>
      <div className="review-navigation"><span>Candidate {current < 0 ? 0 : current + 1} of {candidates.length}</span><button type="button" onClick={() => navigate(-1)} disabled={current <= 0}>← Previous</button><button type="button" onClick={() => navigate(1)} disabled={current >= candidates.length - 1}>Next →</button><button type="button" onClick={() => nextUnreviewed && onSelect(nextUnreviewed.candidate_id)} disabled={!nextUnreviewed}>Next unreviewed</button></div>
    </>}
  </section>;
}
