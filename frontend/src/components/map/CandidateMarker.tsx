import { useMemo } from 'react';
import { divIcon } from 'leaflet';
import { Marker, Popup, Tooltip, useMap } from 'react-leaflet';
import type { HumanReview } from '../../review/reviewStore';
import type { MapPoint } from './mapData';
import { DecisionBadge } from '../ui/Display';
import ReviewStatusBadge from '../review/ReviewStatusBadge';

type Props = { point: MapPoint; selected: boolean; review?: HumanReview; onSelect: (id: string) => void };

export default function CandidateMarker({ point, selected, review, onSelect }: Props) {
  const map = useMap();
  const { candidate, index, latitude, longitude } = point;
  const icon = useMemo(() => divIcon({
    className: `sonar-marker status-${candidate.decision.status.toLowerCase()} ${selected ? 'selected' : ''}`,
    html: `<span>${String(index + 1).padStart(2, '0')}</span>`,
    iconSize: selected ? [42, 42] : [34, 34],
    iconAnchor: selected ? [21, 21] : [17, 17],
  }), [candidate.decision.status, index, selected]);
  const position: [number, number] = [latitude, longitude];
  const select = () => { onSelect(candidate.candidate_id); map.panTo(position); };
  return <Marker position={position} icon={icon} title={`Candidate ${index + 1}, ${candidate.detection.class_name}, AI ${candidate.decision.status}`} alt={`Candidate ${index + 1}, ${candidate.detection.class_name}, AI ${candidate.decision.status}`} eventHandlers={{ click: select }}>
    <Tooltip direction="top" offset={[0, -20]}>{`#${String(index + 1).padStart(2, '0')} ${candidate.detection.class_name} · ${candidate.decision.status}`}</Tooltip>
    <Popup><div className="sonar-popup"><strong>CANDIDATE #{String(index + 1).padStart(2, '0')}</strong><h3>{candidate.detection.class_name}</h3><dl><dt>AI decision</dt><dd><DecisionBadge status={candidate.decision.status} /></dd><dt>Fusion</dt><dd>{candidate.decision.fusion_score}</dd><dt>Source</dt><dd>{candidate.detection.source_mode}</dd><dt>Human review</dt><dd><ReviewStatusBadge status={review?.status ?? 'NOT_REVIEWED'} /></dd></dl><p>WGS84 · {latitude.toFixed(6)}, {longitude.toFixed(6)}</p><button type="button" onClick={select}>Inspect candidate</button></div></Popup>
  </Marker>;
}
