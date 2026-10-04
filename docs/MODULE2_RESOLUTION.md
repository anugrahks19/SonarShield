# M2.03 — resolution and tiling comparison

Completed 3 October 2026. One successful full comparison on all 1,129 pinned DEV images using the archived epoch-59 detector. No training, HF calls, driver/package changes, production changes or checkpoint replacement.

## Compared strategies

1. Global 640px inference (reference).
2. Global 960px inference, unchanged model weights.
3. Tiled-only: 384px original-raster tiles, 288px stride (25% overlap), each inferred at 640px.
4. Global 640 plus those tiles, with class-aware duplicate merging at IoU 0.70.

Tiles cover edges with shifted full tiles; small images use their available extent. There are no padded edge slivers. This experimental strategy differs from the production detector's conditional tiling and does not certify that implementation. Mean tile count 4.43 per image; maximum 49. Scores use class-correct confidence-ordered one-to-one matching at IoU >=0.50. NMS IoU 0.70, confidence floor 0.001, max_det 300, batch 1 FP32.

## Main results — fixed confidence 0.25

| Strategy | Precision | Recall | TP | FP | FN | Mean local pipeline ms/image |
|---|---:|---:|---:|---:|---:|---:|
| Global 640 | 75.95% | 39.12% | 897 | 284 | 1,396 | 25.56 |
| Global 960 | 67.74% | 40.30% | 924 | 440 | 1,369 | 36.86 |
| Tiles only | 39.90% | 43.48% | 997 | 1,502 | 1,296 | 107.37 |
| Global + tiles | 39.84% | 49.50% | 1,135 | 1,714 | 1,158 | 132.88 |

640 exactly reproduces M2.01/M2.02 TP/FP/FN. No strategy reached precision and recall >=80% together on the 18-point threshold grid. Best overall grid F1: 640 53.87%, 960 51.84%, tiles 41.61%, global+tiles 44.15%. Threshold choices here are exploratory DEV diagnostics, not deployed thresholds.

Timing caveat: two initial evaluations crashed natively (CUDA driver 0xc0000409; Python 0xc0000005). Only those identified evaluation processes were stopped. A retry completed with `CUDA_LAUNCH_BLOCKING=1` and one PyTorch CPU thread, preserving each completed image. Measurements exclude warmup, disk decoding, scoring, upload, fusion and UI. Global+tiles time sums global, tiles and merge phases. These times compare strategies within the synchronized run; **they are not comparable to the earlier 9.92ms GPU-forward-only result or normal asynchronous deployment latency**. Native runtime stability on this machine remains a separate issue; no system-level fix is claimed. The cause of the earlier training interruption remains unknown.

## Small-object and class findings

Small size buckets are held constant using original box area scaled to the 640px reference, so changing inference resolution does not move GT between buckets.

| Small-class recall at 0.25 | Global 640 | Global 960 | Tiles | Global+tiles |
|---|---:|---:|---:|---:|
| Crab pot (1,248 GT) | 20.99% | 21.79% | 26.76% | 32.77% |
| Shipwreck (136 GT) | 15.44% | 20.59% | 18.38% | 25.00% |
| Mine (157 GT) | 60.51% | 52.87% | 61.78% | 71.34% |

960 gained 187 GT matches but lost 160 compared with 640: net +27. It gained 114 crab pots and lost 96; gained 65 shipwrecks and lost 39; gained 8 mines and lost 25. Merely changing inference resolution is not a uniform improvement.

Global+tiles gained 241 GT matches and lost 3: net +238. That recovery came with +1,430 FP. Pipeline/net recall remained 100% on this DEV but tiled processing produced many extra detections. Ghost-net data is documented as fully synthetic; these are not real-net field results.

## Duplicate behavior and cap limits

Remaining same-class duplicate-overlap FP at confidence 0.25: global640 40; global960 46; tiles 283; global+tiles 355. Class-aware NMS suppresses overlapping boxes but does not remove all fragments or competing partial detections; blindly lowering merge IoU may also merge neighboring real targets.

No native global or individual tile prediction pass reached max_det 300. Final merged outputs reached the cap for 36 tiled-only and 45 global+tiles images, affecting low-confidence proposal evaluation. None had a 300th retained prediction with confidence >=0.25, so this cap does not truncate the displayed fixed-threshold results. Very-low-threshold tile recall/AP remains conditional on the declared cap.

## Recall-constrained threshold comparisons

These are the best grid points with recall **at least** the listed minimum, not exactly matched/interpolated recall. Exact operating-point calibration still belongs to later phases.

| Minimum recall | Global 640 precision / actual recall | Global 960 | Tiles | Global+tiles |
|---|---|---|---|---|
| 40% | 72.35% / 42.22% | 67.74% / 40.30% | 41.14% / 40.78% | 44.70% / 41.78% |
| 50% | 54.56% / 51.11% | 44.81% / 52.16% | 29.31% / 52.68% | 37.14% / 52.59% |
| 60% | 25.15% / 63.50% | 18.55% / 65.50% | 15.60% / 62.54% | 25.08% / 61.88% |

This does not support enabling unconditionally higher resolution or tiling in the current public model.

## Diagnostic AP protocol

For comparison of remapped tiled boxes, this experiment uses 101-point Ultralytics AP integration with the declared confidence-ordered matching independently at IoU 0.50–0.95. Its matching differs from the earlier validator protocol. Values must not be substituted for the baseline's official validator mAP50 71.89% / mAP50-95 50.05%.

| Strategy | Diagnostic mAP50 | Diagnostic mAP50-95 |
|---|---:|---:|
| Global 640 | 70.57% | 47.88% |
| Global 960 | 65.49% | 38.13% |
| Tiles | 45.82% | 22.32% |
| Global+tiles | 57.57% | 35.73% |

## Decision and next phase

Keep 640 as the reference. Do not select 960 or unconditionally tiled inference for deployment from these results. Small-target recovery is possible, but ranking/localization/background errors and tile duplicates offset it.

Next: **M2.04 source audit**, then M2.05 annotation review and M2.06 reviewed dataset construction. Prioritize crab-pot scale/context annotations, shipwreck mask-to-instance boxes, hard background review, actual acquisition grouping and real net evidence. Train the reviewed five-class detector at 640 first. Native 960 training or other tile/merge designs may be revisited later; their performance is not established by this unchanged-weight inference experiment.

## Artifacts and reproducibility

- [Machine-readable evidence](metrics/module2-resolution-20261003.json).
- Local caches, image progress files, chart and dashboard: `.temp/module2-resolution-synchronized-20261003/`.
- Script: `scripts/compare_module2_resolution.py`.
- Verified: tile coverage, class-aware merge behavior, perfect-case AP, all strategy/class totals, baseline reproduction and checkpoint hashes.

Use a new output folder for reproduction. Training is never invoked. `--resume-from` accepts only a completed-image cache with the same checkpoint, dataset and declared protocol. Existing dataset roles, public XTF gate and deployed artifacts are unchanged. DEV labels remain inherited and historically used; results are not independent field evaluation.
