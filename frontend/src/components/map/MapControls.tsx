import { latLngBounds } from 'leaflet';
import { useMap } from 'react-leaflet';
import type { MapPoint } from './mapData';

export function fitCandidates(map: ReturnType<typeof useMap>, points: MapPoint[]) {
  if (points.length === 0) return;
  if (points.length === 1) map.setView([points[0].latitude, points[0].longitude], 12);
  else map.fitBounds(latLngBounds(points.map(point => [point.latitude, point.longitude] as [number, number])), { padding: [45, 45], maxZoom: 14 });
}

export default function MapControls({ points, showLabels, onToggleLabels }: { points: MapPoint[]; showLabels: boolean; onToggleLabels: () => void }) {
  const map = useMap();
  return <div className="sonar-map-controls" role="toolbar" aria-label="Map controls">
    <button type="button" aria-label="Zoom map in" onClick={() => map.zoomIn()}>+</button>
    <button type="button" aria-label="Zoom map out" onClick={() => map.zoomOut()}>−</button>
    <button type="button" onClick={() => fitCandidates(map, points)}>Fit candidates</button>
    <button type="button" onClick={() => fitCandidates(map, points)}>Reset view</button>
    <button type="button" aria-pressed={showLabels} onClick={onToggleLabels}>{showLabels ? 'Labels on' : 'Labels off'}</button>
  </div>;
}
