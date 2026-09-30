import { useEffect, useRef } from 'react';
import type { Candidate } from '../../types';
import type { HumanReviewStatus } from '../../review/reviewStore';
import { reviewLabel } from './ReviewStatusBadge';

type Props = { candidate: Candidate; status: HumanReviewStatus | 'RESET'; onConfirm: () => void; onCancel: () => void };

export default function ReviewConfirmationDialog({ candidate, status, onConfirm, onCancel }: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
      if (event.key === 'Tab') {
        const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>('.review-dialog button'));
        const first = buttons[0], last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); previous?.focus(); };
  }, [onCancel]);
  return <div className="review-dialog-backdrop"><div className="review-dialog" role="dialog" aria-modal="true" aria-labelledby="review-dialog-title">
    <span className="eyebrow">HUMAN REVIEW</span><h3 id="review-dialog-title">{status === 'RESET' ? 'Reset local review?' : 'Confirm human assessment'}</h3>
    <div className="review-dialog-grid"><span>Candidate</span><strong>{candidate.candidate_id}</strong><span>AI class</span><strong>{candidate.detection.class_name}</strong><span>AI decision</span><strong>{candidate.decision.status}</strong><span>Human assessment</span><strong>{status === 'RESET' ? 'NOT REVIEWED' : reviewLabel(status)}</strong></div>
    {status === 'RESET' && <p>The local assessment, notes, and timestamp will be removed. The AI result stays unchanged.</p>}
    <div className="review-dialog-actions"><button ref={cancelRef} type="button" className="secondary" onClick={onCancel}>Cancel</button><button type="button" className="primary" onClick={onConfirm}>{status === 'RESET' ? 'Reset review' : 'Confirm review'}</button></div>
  </div></div>;
}
