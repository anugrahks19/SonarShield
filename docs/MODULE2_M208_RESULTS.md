# M2.08 completed run measurement

Measured 4 October 2026. 15/15 epochs completed; best checkpoint matches epoch 14. Historical DEV: 1,129 images, 2,293 ground-truth boxes. This is exploratory DEV, not independent test or XTF accuracy.

| Metric | D1 | M2.08 |
|---|---:|---:|
| Precision | 75.97% | 75.57% |
| Recall | 43.70% | 44.66% |
| mAP50 | 70.71% | 69.90% |
| mAP50-95 | 50.01% | 49.73% |
| False positives | 317 | 331 |

Precision/recall/FP above use confidence 0.25, class-correct one-to-one IoU >=0.50, NMS IoU 0.7, 640px. mAP uses the full validation scoring protocol.

Batch-1 FP32 RTX 4060 Laptop GPU model forward: mean 7.53ms, median 6.48ms, p95 10.09ms. Local prediction directory wall time: 10.92ms/image; cloud transfer and evidence fusion excluded.

Ultralytics validator mean-class P/R at its selected F1 point: 77.38% / 69.69%. These differ from fixed-threshold object-micro P/R and must not be substituted into that table.

| Class | Precision at 0.25 | Recall at 0.25 | FP |
|---|---:|---:|---:|
| crab_pot | 72.41% | 29.02% | 141 |
| submarine_pipeline | 99.32% | 100.00% | 1 |
| shipwreck | 67.88% | 44.67% | 115 |
| ghost_net | 100.00% | 100.00% | 0 |
| mine_cylinder | 63.55% | 67.19% | 74 |

Net results are on the inherited synthetic-net examples; they do not establish real ghost-net performance.

Conclusion: recall improved slightly; precision and mAP declined and FP increased. The 80/80 goal was not met at the measured operating point. No model promotion, deployment, training restart or HF calls occurred. Retain D1 until M2.09 compares operating thresholds and any justified candidate selection.

Detailed evidence: [measurement JSON](metrics/module2-m208-evaluation-20261004.json).
