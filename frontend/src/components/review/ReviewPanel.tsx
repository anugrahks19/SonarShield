import { useState } from 'react';
import { Check, X, TriangleAlert } from 'lucide-react';
import type { Candidate } from '../../types';
import type { HumanReview, HumanReviewStatus } from '../../review/reviewStore';
import ReviewConfirmationDialog from './ReviewConfirmationDialog';
import ReviewStatusBadge from './ReviewStatusBadge';

type Props = { analysisId: string; candidate: Candidate; review: HumanReview | undefined; onSave: (review: HumanReview) => boolean; onDelete: () => boolean };
const actions: Array<{ status: Exclude<HumanReviewStatus, 'NOT_REVIEWED'>; label: string; icon: typeof Check }> = [
  { status: 'CONFIRMED', label: 'Confirm target', icon: Check },
  { status: 'FALSE_POSITIVE', label: 'False positive', icon: X },
  { status: 'NEEDS_INVESTIGATION', label: 'Needs investigation', icon: TriangleAlert },
];

export default function ReviewPanel({ analysisId, candidate, review, onSave, onDelete }: Props) {
  const [status, setStatus] = useState<HumanReviewStatus>(review?.status ?? 'NOT_REVIEWED');
  const [note, setNote] = useState(review?.note ?? '');
  const [confirmation, setConfirmation] = useState<HumanReviewStatus | 'RESET' | null>(null);
  const [storageError, setStorageError] = useState(false);
  const closeDialog = () => setConfirmation(null);
  const confirm = () => {
    if (confirmation === 'RESET') {
      if (onDelete()) { setStatus('NOT_REVIEWED'); setNote(''); setStorageError(false); }
      else setStorageError(true);
    } else if (confirmation && confirmation !== 'NOT_REVIEWED') {
      if (onSave({ analysisId, candidateId: candidate.candidate_id, status: confirmation, note, reviewedAt: new Date().toISOString() })) setStorageError(false);
      else setStorageError(true);
    }
    closeDialog();
  };
  return <section className="human-review" id="human-review" aria-label="Human review">
    <div className="human-review-head"><div><span className="eyebrow">HUMAN REVIEW</span><h3>Reviewer assessment</h3></div><span className="local-review-tag" title="Stored in this browser only. Not submitted to F8.">LOCAL SESSION</span></div>
    <div className="review-current"><span>RECORDED HUMAN ASSESSMENT</span><ReviewStatusBadge status={review?.status ?? 'NOT_REVIEWED'} /></div>
    <div className="review-audit"><span>Reviewer: LOCAL SESSION</span><span>Reviewed locally: {review ? new Date(review.reviewedAt).toLocaleString() : 'NOT AVAILABLE'}</span><span>AI result generated: {candidate.provenance.processing_timestamp ? new Date(candidate.provenance.processing_timestamp).toLocaleString() : 'NOT AVAILABLE'}</span></div>
    <fieldset className="review-actions"><legend>Choose an assessment</legend>{actions.map(action => <button key={action.status} type="button" aria-pressed={status === action.status} className={`review-action review-action-${action.status.toLowerCase()} ${status === action.status ? 'is-selected' : ''}`} onClick={() => setStatus(action.status)}><action.icon size={15} aria-hidden="true" />{action.label}</button>)}</fieldset>
    <label className="review-notes">REVIEWER NOTES<textarea value={note} onChange={event => setNote(event.target.value)} placeholder="Add observations…" rows={4} /></label>
    <div className="review-save-row"><button type="button" className="primary" disabled={status === 'NOT_REVIEWED'} onClick={() => setConfirmation(status)}>Save review</button>{review && <button type="button" className="secondary" onClick={() => setConfirmation('RESET')}>Reset review</button>}</div>
    {storageError && <p className="review-storage-error" role="alert">Could not save local review state in this browser. The assessment was not recorded.</p>}
    <p className="review-local-note">Human notes and assessment are stored only in this browser. The F8 AI decision is unchanged.</p>
    {confirmation && <ReviewConfirmationDialog candidate={candidate} status={confirmation} onConfirm={confirm} onCancel={closeDialog} />}
  </section>;
}
