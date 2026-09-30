import { useState } from 'react';
import type { Candidate } from '../../types';
import { locationState } from './mapData';

export default function LocationDetails({ candidate, index, onViewInSonar }: { candidate: Candidate | null; index: number; onViewInSonar: () => void }) {
  const [copied, setCopied] = useState(false);
  if (!candidate) return <div className="location-details"><span className="eyebrow">LOCATION DETAIL</span><p>Select a candidate to inspect its backend coordinates.</p></div>;
  const state = locationState(candidate);
  const { image, sonar, geographic } = candidate.localization.coordinates;
  const envelope = candidate.localization_uncertainty.error_envelope;
  const copy = async (value: string) => {
    try { await navigator.clipboard.writeText(value); setCopied(true); window.setTimeout(() => setCopied(false), 1800); } catch { setCopied(false); }
  };
  return <div className="location-details"><span className="eyebrow">LOCATION DETAIL · CANDIDATE #{String(index + 1).padStart(2, '0')}</span><h3>{candidate.detection.class_name}</h3>
    <div className="location-state"><span>BACKEND STATUS</span><strong>{candidate.localization.metadata.status}</strong>{state === 'INVALID' && <em>LOCATION DATA INVALID</em>}</div>
    {image && <div className="coordinate-group"><h4>IMAGE PIXEL · {image.coordinate_system}</h4><div><span>Center X</span><strong>{image.center_x}</strong></div><div><span>Center Y</span><strong>{image.center_y}</strong></div></div>}
    {sonar && <div className="coordinate-group"><h4>SONAR COORDINATE · {sonar.coordinate_system}</h4><div><span>Range</span><strong>{sonar.range_m ?? 'NOT AVAILABLE'}</strong></div><div><span>Along track</span><strong>{sonar.along_track_m ?? 'NOT AVAILABLE'}</strong></div><div><span>Across track</span><strong>{sonar.across_track_m ?? 'NOT AVAILABLE'}</strong></div></div>}
    {state === 'GEOGRAPHIC' && geographic ? <div className="coordinate-group"><h4>LATITUDE / LONGITUDE · {geographic.coordinate_system}</h4><div><span>Latitude</span><strong>{geographic.latitude.toFixed(6)}</strong></div><div><span>Longitude</span><strong>{geographic.longitude.toFixed(6)}</strong></div><div className="coordinate-copy"><button type="button" onClick={() => void copy(String(geographic.latitude))}>Copy latitude</button><button type="button" onClick={() => void copy(String(geographic.longitude))}>Copy longitude</button><button type="button" onClick={() => void copy(`${geographic.latitude}, ${geographic.longitude}`)}>Copy coordinates</button>{copied && <span role="status">COPIED</span>}</div><button type="button" className="view-sonar" onClick={onViewInSonar}>View in sonar</button></div> : <div className="coordinate-unavailable"><strong>GEOGRAPHIC POSITION NOT AVAILABLE</strong><span>{candidate.localization.metadata.reason_code}</span></div>}
    <div className="coordinate-group"><h4>LOCALIZATION UNCERTAINTY · BACKEND REFERENCE</h4><div><span>Status</span><strong>{envelope.status}</strong></div><div><span>Scope</span><strong>{envelope.scope}</strong></div><div><span>Pixel envelope</span><strong>{envelope.envelope_px === null ? 'NOT ESTIMABLE' : `${envelope.envelope_px} px`}</strong></div><p>Class-conditional validation reference; no geographic uncertainty region is provided by F7.</p></div>
    {candidate.quality.localization.flags.length > 0 && <div className="coordinate-group"><h4>BACKEND LOCATION FLAGS</h4>{candidate.quality.localization.flags.map(flag => <p key={flag.code}>{flag.severity}: {flag.code}</p>)}</div>}
  </div>;
}
