# M2.01 — preserved exploratory baseline

Completed 3 October 2026. This is the **Preserve and benchmark** module in the ordered 80+ roadmap. It does not close the earlier scientific dataset/provenance audit that also used the M2.01 label.

## Preserved identities and evidence

- Canonical dataset: `datasets/controlled_v8a_20261003`; 12,213 TRAIN and 1,129 DEV images.
- Verified every manifest image, annotation, source image and source annotation against pinned hashes; checked role/path pairing, class coverage and exact byte/pixel/parent TRAIN–DEV boundaries with the existing preflight.
- Run: `models/controlled/v8a_labels_fixed_01`; `last.pt` retains 60 completed epochs of 80 and optimizer state. `best.pt` is epoch 59. Training was not resumed. The interruption cause remains unknown.
- Private archive: `.temp/module2-baseline-preserved-20261003`. Contains both checkpoints, run args/results, dataset YAML/manifest/readiness, evaluation report, per-image metrics, evaluator source and baseline evidence. Copies and unchanged source inputs were SHA-256 verified.
- Checked-in-sized evidence: [baseline-evidence.json](metrics/module2-baseline-20261003.json). Model/data files stay local; the archive can reconstruct identities but is not a second full dataset copy. It remains on the same disk, so it is not protection against disk failure.

## Measured baseline

Measurements reuse the completed epoch-59 evaluation, whose checkpoint hashes and DEV image identities were reconciled during preservation. No evaluation or training was repeated for this module.

| Metric | Value | Definition |
|---|---:|---|
| Precision / recall | 75.95% / 39.12% | Object micro, confidence 0.25, class-correct one-to-one IoU >=0.50 |
| TP / FP / FN | 897 / 284 / 1,396 | Same fixed operating point |
| False positives per image | 0.25155 | Against inherited DEV annotations |
| Validator precision / recall | 76.42% / 70.23% | Mean class values at validator-selected F1 point, not the fixed-point micro values |
| mAP50 / mAP50-95 | 71.89% / 50.05% | Detector validation, confidence floor 0.001, NMS IoU 0.70 |
| Forward mean / median / p95 | 9.92 / 7.44 / 17.51 ms | RTX 4060 Laptop, FP32, batch 1, warmed detector-only prediction at 640px |

Directory traversal, prediction and scoring wall time averaged 14.00 ms/image. Neither timing includes fusion, upload/network, UI or raw XTF processing. Per-image and per-class TP/FP/FN totals reconcile to the report. The dataset has 2,293 DEV ground-truth objects.

## Safeguards and reproducibility

The new `scripts/preserve_module2_baseline.py` refuses an existing output directory, changed checkpoint/data identities, mismatched evaluation image identities, inconsistent totals, changed checkpoint epochs or source changes during archiving. It imports no training execution path and makes no inference/network calls. It records installed package versions; leave that environment unchanged for subsequent comparisons.

To reproduce preservation later, use a **new** archive directory, while the source baseline identities are unchanged:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/preserve_module2_baseline.py --output .temp/module2-baseline-recheck-01
```

If training resumes, the original evidence remains valid for its archived epoch-59 checkpoint; the current source `last.pt` will differ, so this script intentionally refuses to treat it as the unchanged baseline.

## Scope and next step

M2.01 preservation is complete. It establishes an immutable reference for experiments, not 80+ accuracy or an independent benchmark. Labels are inherited, DEV has historical usage, semantic correctness/near duplicates/source licenses and untouched acquisition groups remain unresolved. XTF accuracy, calibration and public deployment gates are unchanged.

Next: **M2.02 — diagnose detection failures**, with prediction/threshold curves, class/size/source breakdowns and a review gallery. No new long training run is warranted by preservation alone.
