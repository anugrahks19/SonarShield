# M2.10 final short-run measurement

Measured 4 October 2026. User training completed 10/10 epochs; best.pt matches epoch 6. Same historical DEV: 1,129 images / 2,293 annotated objects. No training restarted, deployment or HF calls.

| Metric | D1 | M2.08 | M2.10 |
|---|---:|---:|---:|
| Precision | 75.97% | 75.57% | 76.07% |
| Recall | 43.70% | 44.66% | 43.26% |
| mAP50 | 70.71% | 69.90% | 70.35% |
| mAP50–95 | 50.01% | 49.73% | 49.89% |
| GPU model forward ms/image | 7.43 | 7.53 | 8.23 |
| False positives | 317 | 331 | 312 |

P/R/FP use confidence 0.25, class-correct one-to-one matching IoU >=0.50, NMS IoU 0.7 and 640px. mAP uses the full validator protocol. Timing is warmed batch-1 FP32 on RTX 4060 Laptop GPU; separate sessions may have different load/thermals.

M2.10 local directory processing wall time: 12.14ms/image, median model forward 6.74ms, p95 12.45ms. Excludes fusion and cloud/network time.

Validator mean-class P/R at its selected F1 point: 76.63% / 69.08%. These are not the fixed-0.25 micro metrics in the table.

| Class | Precision | Recall | FP |
|---|---:|---:|---:|
| crab_pot | 71.58% | 27.06% | 137 |
| submarine_pipeline | 98.66% | 100.00% | 2 |
| shipwreck | 69.74% | 44.49% | 105 |
| ghost_net | 100.00% | 100.00% | 0 |
| mine_cylinder | 64.40% | 64.06% | 68 |

Net figures refer to inherited synthetic examples; real ghost-net accuracy is unverified.

## Decision

Bias warmup was corrected, but the final candidate did not produce a broad quality improvement. Relative to D1 at confidence 0.25: slightly higher precision and five fewer FP, but lower recall and mAP. The 80/80 goal remains unmet at this point. Preserve candidates; no automatic promotion. No third training run is planned. Next: compare the final candidate at the same precision-floor objective, then freeze compatible artifacts and complete submission QA/packaging.

DEV has been reused for training validation and experiment selection; these figures are not independent final-test or XTF accuracy.

[Detailed measurement](metrics/module2-m210-evaluation-20261004.json).
