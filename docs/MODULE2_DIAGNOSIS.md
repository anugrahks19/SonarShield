# M2.02 — failure diagnosis

Completed 3 October 2026. No training, calibration fitting, model promotion or HF calls. One local GPU prediction pass was made; report/gallery refinement reused that cache.

## Evidence and settings

Archived epoch-59 `best.pt`, SHA-256 `8756f872eba701edd8a75163d4991defe03945501649290008d08579326a6e93`; pinned corrected DEV manifest. All 1,129 images/labels were hash verified. Settings: 640px, RTX 4060 GPU, batch 1, FP32, confidence floor 0.001, class-aware NMS IoU 0.70, max_det 300. No image reached the 300 prediction cap.

Matching: confidence-ordered, class-correct, one-to-one IoU >=0.50. Cached predictions filtered at 0.25 exactly reproduced the preserved baseline: TP 897, FP 284, FN 1,396. Synthetic scoring checks covered duplicate protection, wrong classes, confidence rejection, IoU rejection and size buckets.

- Summary: [machine-readable report](metrics/module2-diagnosis-20261003.json).
- Private predictions, full review queue, 49-image gallery and plot: `.temp/module2-failure-diagnosis-final-20261003/`.
- Gallery entry point: `index.html`. Green boxes are inherited ground truth; orange boxes are retained predictions at confidence >=0.25. Gallery shows representative errors and deterministic random controls; it is not a representative sample for calculating accuracy.

## 1. Confidence changes did not reach 80/80

| Threshold | Micro precision | Micro recall | FP |
|---|---:|---:|---:|
| 0.001 | 8.49% | 72.53% | 17,935 |
| 0.05 | 47.07% | 54.38% | 1,402 |
| 0.10 | 59.71% | 49.06% | 759 |
| 0.25 | 75.95% | 39.12% | 284 |
| 0.40 | 85.19% | 33.10% | 132 |
| 0.50 | 90.27% | 29.13% | 72 |

None of 18 tested thresholds achieved precision and recall >=80% overall. Best overall micro F1 on this finite grid was 53.87% at 0.10; that is a diagnostic DEV selection, not a recommended production threshold. Pipeline and ghost-net classes pass 80/80 at some grid points; crab pots, shipwrecks and mines do not. No threshold tested meets the goal for all five classes simultaneously.

These object micro values cannot be compared directly with validator mean-class P/R at its selected F1 point. The latter weights classes differently; micro recall is heavily influenced by 1,275 crab-pot objects. No detector mAP recalculation or speed benchmark was required for this diagnosis; M2.01 retains those measurements.

## 2. Target-size findings at confidence 0.25

Sizes use box area after scaling the image's longest side to 640: small <32 squared pixels, medium <96 squared pixels, large otherwise. They are raster-area strata, not physical dimensions; elongated objects need separate inspection.

| Class/size | GT objects | Recall |
|---|---:|---:|
| Crab pot, small | 1,248 | 20.99% |
| Crab pot, medium | 26 | 23.08% |
| Shipwreck, small | 136 | 15.44% |
| Shipwreck, medium | 187 | 24.60% |
| Shipwreck, large | 221 | 73.30% |
| Mine, small | 157 | 60.51% |
| Mine, medium | 34 | 64.71% |

97.9% of DEV crab-pot boxes are small by this definition. This supports a controlled 640/960/tile comparison in M2.03; it does not establish that higher resolution will solve the problem. Crab-pot medium/large support is too small for broad size-generalization claims.

## 3. Overlap diagnostics: hypotheses for annotation review

| Class | Misses | Low-score same-class overlap | No retained overlap | Retained localization overlap | Other |
|---|---:|---:|---:|---:|---:|
| Crab pot | 1,007 | 552 | 434 | 21 | 0 |
| Shipwreck | 315 | 155 | 135 | 24 | 1 competition case |
| Mine | 74 | 59 | 15 | 0 | 0 |

Low-score overlap means a same-class candidate below 0.25 overlaps that GT at IoU >=0.50. It is not a promise that lowering the threshold recovers all those objects: candidates may compete for GT, and extra false positives enter. Categories are assigned in priority order and are not mutually independent physical causes.

Shipwreck false positives: 66 same-class localization overlaps, 29 duplicate overlaps and 42 unmatched regions. This prioritizes precise mask/instance-box review and duplicate behavior. Crab-pot FP: 41 localization overlaps, 6 duplicate overlaps and 56 unmatched regions. Mine FP: 6 localization overlaps, 5 duplicate overlaps and 30 unmatched regions.

An unmatched region is not certified natural background. It may represent background confusion or an omitted annotation. No labels were altered. The full queue contains every missed GT and unmatched retained prediction, with box/score/size information where applicable.

## 4. Source and evaluation gaps

Filename namespace counts: Contact 502, milco 52, mine 43, pipe 147, synth 135, wreckA 157, wreckR 93. Namespace-specific metrics are in the JSON; these prefixes are **not verified survey/site identities** and cannot establish acquisition-disjoint splits.

The local `datasets/drishti_sss_v3/README.md` explicitly documents `ghost_net` as 100% synthetic and synthetic-on-synthetic evaluation. Its high DEV recall therefore does not demonstrate real ghost-net detection. Confirmed real net imagery/annotations are needed for field claims.

Every DEV image has at least one inherited GT object. Consequently this DEV pool does not independently measure false alarms on a confirmed target-free background set. Review additional natural negatives before reporting background-specific false-alarm performance.

## 5. Ranked actions

1. M2.03: compare resolution/tiling using the same checkpoint, inputs and class-correct scoring; record proposal recovery, localization, duplicate merging and latency.
2. M2.04–05: review small crab-pot labels and context, shipwreck instance/mask boundaries, and natural-background candidate negatives; recover native provenance before combining sources.
3. Obtain real ghost-net labels and reserve untouched groups. Synthetic DEV performance must remain separately labelled.
4. M2.06: create the reviewed revision, including all visible targets in crops and preserving parent/acquisition separation.
5. Train D1 only after the new revision's review and preflight. Preserve pipeline/net/mine coverage while fixing crab-pot and shipwreck failures.

These diagnostics do not justify training on the historical final test, relabelling model outputs as truth, changing production thresholds or enabling public XTF inference.
