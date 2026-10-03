"""Sample whole survey days into distinct roles. No inference, training or labels."""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.runtime.xtf import packets, windows
from ai.runtime.pipeline import sha256_file


def prepare(folder, output, rows=256, logs_per_day=2, samples_per_channel=3):
    from PIL import Image
    folder, output = Path(folder), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh directory; never overwrite human annotations.')
    if not 16 <= rows <= 512 or not 1 <= logs_per_day <= 4 or not 1 <= samples_per_channel <= 8:
        raise ValueError('Invalid bounded sampling options.')
    groups = {}
    for path in sorted(folder.glob('*.xtf')):
        match = re.search(r'(15\d{4})\d{6}$', path.stem)
        if not match:
            raise ValueError('Unrecognised source date: ' + path.name)
        groups.setdefault(match[1], []).append(path)
    days = sorted(groups)
    if len(days) < 4:
        raise ValueError('Need at least four acquisition days for development/calibration/holdout roles.')
    output.mkdir(parents=True, exist_ok=True)
    entries, sources = [], []
    # Entire final day is holdout, previous day calibration. No adjacent-window split.
    for day in days:
        split = 'TEST' if day == days[-1] else 'CALIBRATION' if day == days[-2] else 'DEV'
        files = groups[day]
        indices = sorted(set(round(i * (len(files)-1) / max(1, logs_per_day-1)) for i in range(logs_per_day)))
        for index in indices:
            path = files[index]
            source_hash = sha256_file(path)
            reservoir, counts = {}, {}
            rng = random.Random(int(source_hash[:16], 16))
            for gray, ref in windows(packets(path), rows=rows, overlap=0):
                ch = ref['channel']; n = counts.get(ch, 0) + 1; counts[ch] = n
                sample = reservoir.setdefault(ch, [])
                if len(sample) < samples_per_channel:
                    sample.append((gray, ref))
                else:
                    slot = rng.randrange(n)
                    if slot < samples_per_channel:
                        sample[slot] = (gray, ref)
            sources.append({'source_file': path.name, 'sha256': source_hash, 'day': day,
                            'split': split, 'windows_seen_by_channel': counts})
            for ch, selected in sorted(reservoir.items()):
                for gray, ref in sorted(selected, key=lambda item: item[1]['packet_offsets'][0]):
                    name = f'{path.stem}-c{ch}-p{ref["ping_numbers"][0]}.png'
                    Image.fromarray(gray).save(output / name)
                    (output / (name+'.source.json')).write_text(json.dumps(ref, allow_nan=False), encoding='utf-8')
                    entries.append({'image': name, 'image_sha256': sha256_file(output / name),
                                    'width': gray.shape[1], 'height': gray.shape[0],
                                    'source_sha256': source_hash, 'source_file': path.name,
                                    'acquisition_group': 'USGS_2015-315-FA_15CCT03', 'day': day,
                                    'split': split, 'channel': ch, 'ping_start': ref['ping_numbers'][0],
                                    'rendering_version': ref['rendering_metadata']['version'],
                                    'annotation_status': 'UNREVIEWED_NOT_A_NEGATIVE'})
            print(f'{split}: {path.name}: sampled {sum(map(len,reservoir.values()))} windows', flush=True)
    manifest = {'version': 1, 'sampling': 'DETERMINISTIC_RESERVOIR_PER_CHANNEL_NO_PREDICTION_SELECTION',
                'scope': 'ONE_SURVEY_DAY_GROUPED_NOT_INDEPENDENT_EXTERNAL_VALIDATION',
                'test_day': days[-1], 'calibration_day': days[-2], 'sources': sources, 'images': entries,
                'rendering_source_sha256': sha256_file(Path(__file__).resolve().parents[1]/'ai/runtime/sonar_rendering.py')}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    template = {'version': 1, 'annotations': [{'image_sha256': e['image_sha256'], 'reviewer': '',
                 'status': 'UNREVIEWED', 'objects': [], 'notes': ''} for e in entries]}
    (output/'annotations-template.json').write_text(json.dumps(template, indent=2), encoding='utf-8')
    import shutil
    shutil.copyfile(Path(__file__).with_name('survey_annotation.html'), output/'index.html')
    return manifest


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('folder', type=Path); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--rows', type=int, default=256); p.add_argument('--logs-per-day', type=int, default=2)
    a=p.parse_args(); m=prepare(a.folder,a.output,a.rows,a.logs_per_day)
    print(json.dumps({'images': len(m['images']), 'inference_calls': 0, 'training_started': False}))
