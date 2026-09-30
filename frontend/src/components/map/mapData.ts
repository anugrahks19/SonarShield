import type { Candidate } from '../../types';

export type LocationState = 'GEOGRAPHIC' | 'PIXEL_ONLY' | 'RELATIVE_SONAR' | 'UNAVAILABLE' | 'NOT_PROCESSED' | 'INVALID';
export type MapPoint = { candidate: Candidate; index: number; latitude: number; longitude: number; coordinateSystem: string };

export function locationState(candidate: Candidate): LocationState {
  const status = candidate.localization?.metadata?.status;
  const geographic = candidate.localization?.coordinates?.geographic;
  if (status === 'GEOGRAPHIC') {
    if (!geographic || geographic.coordinate_system !== 'WGS84'
      || !Number.isFinite(geographic.latitude) || !Number.isFinite(geographic.longitude)
      || Math.abs(geographic.latitude) > 90 || Math.abs(geographic.longitude) > 180) return 'INVALID';
    return 'GEOGRAPHIC';
  }
  if (geographic) return 'INVALID';
  if (status === 'PIXEL_ONLY' || status === 'RELATIVE_SONAR' || status === 'UNAVAILABLE' || status === 'NOT_PROCESSED') return status;
  return 'INVALID';
}

export function mapPoints(candidates: Candidate[]): MapPoint[] {
  return candidates.flatMap((candidate, index) => {
    if (locationState(candidate) !== 'GEOGRAPHIC') return [];
    const geographic = candidate.localization.coordinates.geographic!;
    return [{ candidate, index, latitude: geographic.latitude, longitude: geographic.longitude, coordinateSystem: geographic.coordinate_system }];
  });
}
