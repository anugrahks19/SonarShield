# M2.07 D1 measurement — 4 October 2026

User-run D1 completed **80/80 epochs**. Evaluated saved `best.pt`; its embedded training metrics match CSV epoch 75. Finished checkpoints have epoch -1 and no optimizer because they were stripped by the trainer; that is not lost training. No training was restarted and no model was promoted.

## Fresh FP32 DEV measurement

1,129 historically used DEV images, 2,293 inherited ground-truth boxes; 640px, RTX 4060 Laptop GPU. Fixed-confidence object P/R uses confidence 0.25, class-correct one-to-one matching at IoU >=0.50 and NMS IoU 0.70.

| Measurement | Result |
|---|---:|
| Object precision at 0.25 | 75.97% |
| Object recall at 0.25 | 43.70% |
| mAP50 | 70.71% |
| mAP50–95 | 50.01% |
| Batch-1 GPU model forward, mean | 7.43 ms/image |
| Local directory prediction wall time | 10.39 ms/image |
| False positives at 0.25 | 317 |
| False positives/image | 0.281 |
| True positives / false negatives | 1,002 / 1,291 |

mAP comes from standard low-confidence validation, not the fixed 0.25 subset. Model-forward timing excludes upload, API, fusion, review and report generation. Median forward 6.45ms; p95 10.66ms. This is a warm local GPU measurement, not public service latency.

## Per-class fixed-confidence results

| Class | Precision | Recall | FP |
|---|---:|---:|---:|
| Crab pot | 70.45% | 28.24% | 151 |
| Pipeline | 98.66% | 100.00% | 2 |
| Shipwreck | 71.08% | 43.38% | 96 |
| Synthetic ghost net | 99.26% | 100.00% | 1 |
| Mine/cylinder inherited class | 64.92% | 64.58% | 67 |

## Comparison with the preserved reference

At identical fixed confidence and matching on the same DEV image bytes:

| Metric | Preserved candidate (60-epoch run) | D1 (80-epoch run) |
|---|---:|---:|
| Object precision | 75.95% | 75.97% |
| Object recall | 39.12% | 43.70% |
| FP | 284 | 317 |
| Standard mAP50 | 71.89% | 70.71% |
| Standard mAP50–95 | 50.05% | 50.01% |

Results are mixed, not an across-the-board improvement. Recall improved, but false positives increased and mAP50 decreased. Different completed epoch budgets mean this is not an equal-budget isolation of the data change. No 80/80 or 90/90 claim is supported.

## Why these differ from training-log P/R

Fresh standard validation mean-class P/R is **76.59% / 69.79%**, using its validator-selected F1 point. Training's selected epoch recorded **78.13% / 68.71%**, mAP50 70.58%, mAP50–95 49.94%. Training-validation and fresh FP32 inference can differ in numeric execution. Neither mean-class summary is the fixed-confidence micro object P/R above. Do not mix their operating points when claiming precision and recall together.

## Scope and handoff

This is inherited-label historical DEV, not an independent test, verified natural-background pool, real-net benchmark or raw-XTF accuracy certification. All DEV images have labelled objects; FP counts cannot certify target-free field false-alarm performance. Ghost-net evidence remains synthetic. Missing labels may affect evaluation counts. Checkpoint hashes were verified unchanged during evaluation; zero HF calls and no training restart.

Full machine evidence: `docs/metrics/module2-d1-evaluation-20261004.json`. Private per-image evidence and standard validation output: `.temp/module2-d1-evaluation-20261004/`.

M2.07 user training and DEV measurement are complete. M2.08 should address measured small-target/generalization failures and the missing confirmed-negative pool before another long run. Do not automatically deploy D1 or attach older fusion/calibration artifacts.
