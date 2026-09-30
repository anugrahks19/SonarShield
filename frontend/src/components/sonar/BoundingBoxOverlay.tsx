import { memo } from 'react';
import type { Candidate } from '../../types';

type Props = { candidates: Candidate[]; width: number; height: number; selectedId: string | null; onSelect: (id: string) => void };

function BoundingBoxOverlay({ candidates, width, height, selectedId, onSelect }: Props) {
  return <div className="box-overlay" aria-label="Candidate bounding boxes">
    {candidates.map((candidate, index) => {
      const [x1, y1, x2, y2] = candidate.detection.bbox;
      if (![x1, y1, x2, y2].every(Number.isFinite) || x2 <= x1 || y2 <= y1) return null;
      const selected = selectedId === candidate.candidate_id;
      return <button key={candidate.candidate_id} type="button"
        className={`bbox status-${candidate.decision.status.toLowerCase()} ${selected ? 'is-selected' : ''} ${y1 / height < .07 ? 'label-below' : ''}`}
        style={{ left: `${x1 / width * 100}%`, top: `${y1 / height * 100}%`, width: `${(x2 - x1) / width * 100}%`, height: `${(y2 - y1) / height * 100}%` }}
        title={`Candidate #${String(index + 1).padStart(2, '0')} · ${candidate.detection.class_name} · ${candidate.decision.status} · Fusion ${candidate.decision.fusion_score}`}
        aria-label={`Select candidate ${index + 1}, ${candidate.detection.class_name}, ${candidate.decision.status}`}
        aria-pressed={selected} onClick={() => onSelect(candidate.candidate_id)}>
        <span className="candidate-label">#{String(index + 1).padStart(2, '0')} {candidate.detection.class_name} · {candidate.decision.status}</span>
      </button>;
    })}
  </div>;
}

export default memo(BoundingBoxOverlay);
