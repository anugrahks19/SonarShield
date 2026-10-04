"""Verify and archive the measured exploratory baseline; never run inference/training."""
import argparse
import csv
import importlib.metadata
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.train_corrected_candidate import preflight
from ai.training.candidate_data import sha


def preserve(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Use a fresh archive directory; existing evidence is never overwritten.')
    dataset = root / 'datasets/controlled_v8a_20261003'
    run = root / 'models/controlled/v8a_labels_fixed_01'
    evaluation = root / '.temp/interrupted-run-evaluation-20261003'
    print('Verifying pinned TRAIN/DEV images, labels and source lineage; no training.', flush=True)
    checked = preflight(dataset, root / 'models/v6/detector_v6_p2_sss/weights/best.pt')
    report = json.loads((evaluation / 'report.json').read_text(encoding='utf-8'))
    rows = json.loads((evaluation / 'per-image.json').read_text(encoding='utf-8'))
    manifest = json.loads((dataset / 'manifest.json').read_text(encoding='utf-8'))
    dev = [r for r in manifest['records'] if r['split'] == 'DEV']
    if report['images'] != len(dev) or len(rows) != len(dev):
        raise ValueError('Evaluation image count does not match pinned DEV.')
    if Counter(r['image'] for r in rows) != Counter(Path(r['image']).name for r in dev):
        raise ValueError('Evaluation image identities do not match pinned DEV.')
    for key in ('tp', 'fp', 'fn'):
        expected = report['object_metrics'][key]
        if sum(r[key] for r in rows) != expected or sum(r[key] for r in report['per_class'].values()) != expected:
            raise ValueError('Evaluation totals do not reconcile.')
    if report['training_restarted'] or report['hf_inference_calls'] != 0:
        raise ValueError('Unexpected evaluation scope.')
    inputs = {
        'best.pt': run / 'weights/best.pt', 'last.pt': run / 'weights/last.pt',
        'args.yaml': run / 'args.yaml', 'results.csv': run / 'results.csv',
        'data.yaml': dataset / 'data.yaml', 'manifest.json': dataset / 'manifest.json',
        'READY.json': dataset / 'READY.json', 'evaluation.json': evaluation / 'report.json',
        'per-image.json': evaluation / 'per-image.json',
        'evaluator.py': root / 'scripts/evaluate_interrupted_run.py',
    }
    hashes = {name: sha(path) for name, path in inputs.items()}
    if any(hashes[name] != value for name, value in report['checkpoint_sha256'].items()):
        raise ValueError('Checkpoint differs from the measured baseline; evaluate it separately.')
    import torch
    states = []
    for name in ('last.pt', 'best.pt'):
        # Only load the explicitly selected locally produced training checkpoints.
        checkpoint = torch.load(inputs[name], map_location='cpu', weights_only=False)
        states.append({'file': name, 'completed_epochs': checkpoint['epoch'] + 1,
                       'target_epochs': checkpoint['train_args']['epochs'],
                       'optimizer_present': checkpoint.get('optimizer') is not None})
        del checkpoint
    if states != report['checkpoint_states']:
        raise ValueError('Checkpoint state changed since measurement.')
    with inputs['results.csv'].open(encoding='utf-8', newline='') as handle:
        curve = list(csv.DictReader(handle))
    if int(float(curve[-1]['epoch'])) != states[0]['completed_epochs']:
        raise ValueError('CSV and last checkpoint disagree.')
    print('Input identities and cached evaluation reconciled. Archiving checkpoints and evidence.', flush=True)
    output.mkdir(parents=True)
    for name, path in inputs.items():
        shutil.copy2(path, output / name)
        if sha(output / name) != hashes[name]:
            raise ValueError(f'Archive integrity failed: {name}')
    if any(sha(path) != hashes[name] for name, path in inputs.items()):
        raise ValueError('Source changed during preservation; do not accept this snapshot.')
    evidence = {
        'phase': 'M2.01_PRESERVE_AND_BENCHMARK',
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'COMPLETE_FOR_PINNED_EXPLORATORY_BASELINE',
        'dataset': 'datasets/controlled_v8a_20261003',
        'run': 'models/controlled/v8a_labels_fixed_01',
        'dataset_verification': checked, 'checkpoint_states': states,
        'archive_sha256': hashes,
        'package_versions': {p: importlib.metadata.version(p) for p in ('ultralytics', 'torch', 'numpy', 'PyYAML')},
        'baseline': report,
        'verification': {'all_manifest_inputs_verified': True, 'archived_bytes_verified': True,
                         'evaluation_counts_reconciled': True, 'source_unchanged_during_snapshot': True},
        'limits': ['Historically used DEV with inherited labels; not independent final evaluation.',
                   'No new accuracy, XTF, provenance or calibration certification.',
                   'Timing is GPU detector forward only, not full application latency.',
                   'Training interruption cause remains unknown.'],
        'new_training_calls': 0, 'new_inference_calls': 0,
    }
    (output / 'baseline-evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f'BASELINE PRESERVED: {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        preserve(args.root, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'BASELINE NOT ACCEPTED: {error}\n')
