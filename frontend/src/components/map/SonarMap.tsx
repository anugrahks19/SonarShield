import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { AnalyzeResponse } from '../../types';
import type { HumanReview } from '../../review/reviewStore';
import { mapTiles } from '../../config/mapTiles';
import CandidateMarker from './CandidateMarker';
import LocationDetails from './LocationDetails';
import MapControls, { fitCandidates } from './MapControls';
import MapLegend from './MapLegend';
import { locationState, mapPoints } from './mapData';
import type { MapPoint } from './mapData';

function MapViewport({ analysisId, points }: { analysisId: string; points: MapPoint[] }) {
  const map = useMap();
  const coordinates = points.map(point => `${point.candidate.candidate_id}:${point.latitude}:${point.longitude}`).join('|');
  useEffect(() => { fitCandidates(map, points); }, [map, analysisId, coordinates, points]);
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}

type Props = { result: AnalyzeResponse | null; selectedId: string | null; reviews: Record<string, HumanReview>; onSelect: (id: string) => void };

export default function SonarMap({ result, selectedId, reviews, onSelect }: Props) {
  const [showLabels, setShowLabels] = useState(true);
  const [tilesUnavailable, setTilesUnavailable] = useState(false);
  const points = useMemo(() => mapPoints(result?.candidates ?? []), [result]);
  const selectedIndex = result?.candidates.findIndex(candidate => candidate.candidate_id === selectedId) ?? -1;
  const selected = selectedIndex < 0 ? null : result!.candidates[selectedIndex];
  const invalid = result?.candidates.filter(candidate => locationState(candidate) === 'INVALID').length ?? 0;
  const unmapped = (result?.candidates.length ?? 0) - points.length;
  const allPixel = result?.candidates.length && result.candidates.every(candidate => locationState(candidate) === 'PIXEL_ONLY');
  const initial = points[0];
  const viewInSonar = () => document.querySelector('.viewer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  return <section className="sonar-map-section panel" id="geospatial" aria-label="Geospatial workspace">
    <div className="panel-heading sonar-map-heading"><div><span className="eyebrow">GEOSPATIAL WORKSPACE · F7 COORDINATES</span><h2>Candidate localization</h2></div><div className="sonar-map-stats"><span>{result?.candidates.length ?? 0} CANDIDATES</span><strong>{points.length} GEOGRAPHIC</strong><span>{unmapped} UNMAPPED</span></div></div>
    <div className="sonar-map-layout"><div className="sonar-map-main">
      {initial ? <div className="sonar-map-frame">
        <MapContainer center={[initial.latitude, initial.longitude]} zoom={12} zoomControl={false} scrollWheelZoom={true} className={`sonar-leaflet-map ${showLabels ? '' : 'labels-hidden'}`}>
          <TileLayer url={mapTiles.url} attribution={mapTiles.attribution} maxZoom={mapTiles.maxZoom} eventHandlers={{ tileerror: () => setTilesUnavailable(true), tileload: () => setTilesUnavailable(false) }} />
          <MapViewport analysisId={result!.analysis_id} points={points} />
          {points.map(point => <CandidateMarker key={point.candidate.candidate_id} point={point} selected={point.candidate.candidate_id === selectedId} review={reviews[point.candidate.candidate_id]} onSelect={onSelect} />)}
          <MapControls points={points} showLabels={showLabels} onToggleLabels={() => setShowLabels(value => !value)} />
          <MapLegend points={points} />
        </MapContainer>
        {tilesUnavailable && <div className="tile-warning" role="status">MAP TILES UNAVAILABLE · Candidate coordinates remain available.</div>}
      </div> : <div className="sonar-map-empty"><div className="map-empty-glyph">⌖</div><strong>{!result ? 'NO ANALYSIS LOADED' : result.candidates.length === 0 ? 'NO GEOGRAPHIC TARGETS' : invalid ? 'LOCATION DATA INVALID' : 'MAP UNAVAILABLE'}</strong><p>{!result ? 'Analyze a sonar image to inspect backend localization.' : result.candidates.length === 0 ? 'No candidates were returned for this image.' : allPixel ? 'The backend supplied image pixel positions, but no geographic coordinates for this analysis.' : invalid ? 'One or more geographic payloads cannot be plotted safely. The original candidates remain available below.' : 'Geographic coordinates were not supplied for these candidates.'}</p>{result && result.candidates.length > 0 && <span>Image and sonar coordinates, when supplied, remain available in the location detail panel.</span>}</div>}
      <div className="sonar-map-footer"><span>TRACK: NOT PROVIDED BY F7/F8</span><span>GEOGRAPHIC UNCERTAINTY REGION: NOT PROVIDED</span>{unmapped > 0 && result && <span>{unmapped} CANDIDATE{unmapped === 1 ? '' : 'S'} WITHOUT VALID GEOGRAPHIC LOCATION</span>}</div>
    </div><LocationDetails key={`${result?.analysis_id ?? 'none'}:${selectedId ?? 'none'}`} candidate={selected} index={selectedIndex} onViewInSonar={viewInSonar} /></div>
  </section>;
}
