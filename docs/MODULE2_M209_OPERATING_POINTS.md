# M2.09: measured operating-point selection

Completed 4 October 2026. No training, calibration fitting, model promotion, deployment or HF calls. Six unit tests and eight direct greedy-matcher reconciliations passed.

## Scope

Same 1,129 historical DEV images / 2,293 annotated objects. Class-correct confidence-ordered one-to-one matching at IoU >=0.50, 640px, FP32, batch 1, NMS IoU 0.7. Search covered all unique retained post-NMS confidence values, grouping equal scores so tied detections cannot be cherry-picked. D1 predictions were reused with hashes/settings/GT verified; M2.08 required one local prediction pass. Both low-floor caches reproduce the earlier confidence-0.25 TP/FP/FN exactly. Neither cache hit max_det=300.

## One common threshold: maximum measured recall while overall precision >=80%

| Checkpoint | Threshold (approximate) | Precision | Recall | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| D1 | 0.3424893 | 80.07% | 40.12% | 920 | 229 | 1373 |
| M2.08 | 0.3653043 | 80.10% | 41.43% | 950 | 236 | 1343 |

Selected DEV candidate for this objective: M2.08, exact threshold 0.3653043210506439. This is 30 additional true positives versus D1 at its own precision-floor point, with 7 additional FP. Exact machine-readable settings are saved; displayed rounded thresholds must not replace them at boundary-sensitive evaluation.

Overall micro precision >=80% does not guarantee each class has >=80% precision. No 80/80 global point was found.

## Require >=80% precision for every class

| Checkpoint | Overall precision | Overall recall | FP |
|---|---:|---:|---:|
| D1 | 86.39% | 34.06% | 123 |
| M2.08 | 85.93% | 37.03% | 139 |

M2.08 per-class settings:

| Class | Threshold (approximate) | Precision | Recall | FP |
|---|---:|---:|---:|---:|
| crab_pot | 0.5202645 | 80.25% | 20.08% | 63 |
| submarine_pipeline | 0.6193296 | 99.32% | 100.00% | 1 |
| shipwreck | 0.4955001 | 80.68% | 39.15% | 51 |
| ghost_net | 0.8754757 | 100.00% | 100.00% | 0 |
| mine_cylinder | 0.5933417 | 80.33% | 51.04% | 24 |

This policy maximizes each class recall separately subject to its own precision floor. It is not a search over all possible mixed-class threshold combinations under only a global precision constraint. Pipeline and synthetic-net examples perform well; crab-pot, shipwreck and mine recall remain below 80%.

## More recall requires accepting false positives

| Checkpoint | Best micro-F1 threshold | Precision | Recall | FP | Maximum recall in cached pool |
|---|---:|---:|---:|---:|---:|
| D1 | 0.1470489 | 68.38% | 48.28% | 512 | 70.65% |
| M2.08 | 0.1197418 | 66.71% | 49.98% | 572 | 66.25% |

Even retaining every available detection above confidence 0.001 gives recall below 80% for both checkpoints. These are maxima within the cached post-NMS proposal pool, not theoretical architectural limits: different proposal generation or training might change them. Threshold tuning alone cannot recover unproposed or poorly localized targets in this pool.

## Metrics and release decision

mAP is unchanged by this selection report: D1 full-validation mAP50 / mAP50–95 = 70.71% / 50.01%; M2.08 = 69.90% / 49.73%. Do not present threshold selection as an mAP improvement.

M2.09 threshold analysis is complete. Recommend M2.08 only as the candidate for the overall precision-floor objective; deployment compatibility and release checks remain required. Production inference settings, policy/fusion and model weights were not altered. Existing rollback remains intact. No second training run was launched.

The 80/80 goal remains unmet. DEV was already used for validation, recipe design and threshold selection; its results are optimistic exploratory evidence, not an independent final accuracy claim or calibrated probabilities. There are no confirmed natural-negative DEV images, and inherited ghost-net examples are synthetic. Public XTF remains gated.

## Evidence and reproduction

[Full report](metrics/module2-m209-operating-points-20261004.json) · [Candidate settings](metrics/module2-m209-candidate-settings-20261004.json). Private prediction/curve files: `.temp/module2-m209-operating-points-20261004/`.

To repeat, use a fresh output folder:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/select_module2_operating_point.py --output .temp/module2-m209-repeat
```

The repeat command reuses the verified D1 cache and makes one new local M2.08 prediction pass; it never trains or calls HF.
