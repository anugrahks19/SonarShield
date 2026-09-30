"""Read-only F8 smoke test against the locally running frozen backend."""
import hashlib
import json
import os
from pathlib import Path

import requests


BASE = os.environ.get('PHASE8_API_URL', 'http://127.0.0.1:8000').rstrip('/')
ROOT = Path('E:/GITHUB/a sih 2026')
IMAGE = ROOT / 'datasets/drishti_sss_v4/val_clean/images/Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg'

health = requests.get(f'{BASE}/health', timeout=10)
health.raise_for_status()
assert health.json()['status'] == 'OK'

with IMAGE.open('rb') as image:
    detect = requests.post(f'{BASE}/detect', files={'file': (IMAGE.name, image, 'image/jpeg')}, timeout=30)
detect.raise_for_status()
detected = detect.json()
assert detected['summary']['raw_candidate_count'] == 0
assert detected['input']['sha256'] == 'dummy_hash'

with IMAGE.open('rb') as image:
    analyze = requests.post(f'{BASE}/analyze', files={'file': (IMAGE.name, image, 'image/jpeg')}, timeout=180)
analyze.raise_for_status()
analysis = analyze.json()
assert analysis['summary']['candidate_count'] == len(analysis['candidates']) == 2
assert analysis['input']['sha256'] == hashlib.sha256(IMAGE.read_bytes()).hexdigest()
assert {candidate['detection']['source_mode'] for candidate in analysis['candidates']} == {'GLOBAL', 'TILED'}

report = requests.post(f'{BASE}/report', json={'analysis_ids': [analysis['analysis_id']], 'format': 'JSON', 'include_images': False}, timeout=30)
report.raise_for_status()
metadata = report.json()
assert metadata['status'] == 'GENERATED' and metadata['report_id']
artifact_status = requests.get(f"{BASE}{metadata['report_url']}", timeout=10).status_code if metadata.get('report_url') else None
assert artifact_status == 404 and metadata['download_url'] is None and metadata['data'] is None

paths = set(requests.get(f'{BASE}/openapi.json', timeout=10).json()['paths'])
assert {'/health', '/detect', '/analyze', '/report'}.issubset(paths)
assert not any('review' in path for path in paths)
print(json.dumps({'health': health.status_code, 'detect': detect.status_code, 'detect_stub': True, 'analyze': analyze.status_code, 'candidate_count': 2, 'report': report.status_code, 'report_artifact_status': artifact_status, 'review_endpoint': False, 'processing_time_ms': analysis['processing']['processing_time_ms']}))
