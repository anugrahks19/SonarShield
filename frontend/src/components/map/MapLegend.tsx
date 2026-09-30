import type { MapPoint } from './mapData';

export default function MapLegend({ points }: { points: MapPoint[] }) {
  const statuses = [...new Set(points.map(point => point.candidate.decision.status))];
  return <div className="sonar-map-legend" aria-label="Map legend"><span>AI DECISION</span>{statuses.map(status => <span className="legend-item" key={status}><i className={`legend-dot status-${status.toLowerCase()}`} />{status}</span>)}</div>;
}
