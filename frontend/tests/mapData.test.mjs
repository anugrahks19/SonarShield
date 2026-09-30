import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { locationState, mapPoints } from '../src/components/map/mapData.ts';

const outputs = JSON.parse(await readFile(new URL('../../ai/reference/gate_f9_runtime_results.json', import.meta.url), 'utf8'));
const source = outputs.find(output => output.summary.candidate_count === 2);
const clone = value => structuredClone(value);

test('real F9 data stays pixel-only and produces no map markers', () => {
  for (const output of outputs) {
    assert.equal(mapPoints(output.candidates).length, 0);
    for (const candidate of output.candidates) assert.equal(locationState(candidate), 'PIXEL_ONLY');
  }
});

test('map adapter passes through only valid backend WGS84 coordinates', () => {
  const candidates = clone(source.candidates);
  candidates[0].localization.metadata.status = 'GEOGRAPHIC';
  candidates[0].localization.coordinates.geographic = { coordinate_system: 'WGS84', latitude: 10.123456789, longitude: 76.987654321, heading_deg: null };
  assert.equal(locationState(candidates[0]), 'GEOGRAPHIC');
  assert.equal(locationState(candidates[1]), 'PIXEL_ONLY');
  const points = mapPoints(candidates);
  assert.equal(points.length, 1);
  assert.equal(points[0].latitude, 10.123456789);
  assert.equal(points[0].longitude, 76.987654321);
  assert.equal(points[0].candidate, candidates[0]);
  assert.equal(source.candidates[0].localization.coordinates.geographic, null);
});

test('invalid geographic payload is not mapped or replaced by a default point', () => {
  const candidate = clone(source.candidates[0]);
  candidate.localization.metadata.status = 'GEOGRAPHIC';
  assert.equal(locationState(candidate), 'INVALID');
  assert.deepEqual(mapPoints([candidate]), []);
  candidate.localization.coordinates.geographic = { coordinate_system: 'WGS84', latitude: 91, longitude: 0, heading_deg: null };
  assert.equal(locationState(candidate), 'INVALID');
  candidate.localization.coordinates.geographic.latitude = 0;
  candidate.localization.coordinates.geographic.coordinate_system = 'UNSUPPORTED_CRS';
  assert.equal(locationState(candidate), 'INVALID');
  candidate.localization.coordinates.geographic.coordinate_system = 'WGS84';
  assert.equal(locationState(candidate), 'GEOGRAPHIC');
  assert.deepEqual(mapPoints([candidate]).map(point => [point.latitude, point.longitude]), [[0, 0]]);
});
