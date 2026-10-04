# Module 2: dataset index and route to 80+ metrics

> **Submission override — 4 October 2026:** M2.08–M2.12 now follow [the deadline plan](MODULE2_SUBMISSION_PLAN.md): one short D1 fine-tune, at most one conditional second learned run, then freeze, QA and packaging. The earlier 80-epoch D2 launch is superseded; no training has been started by the agent.


Prepared 3 October 2026 from the local dataset tree and measured interrupted-run evaluation. Planning only: no training started, no data rewritten, no production model promoted.

## 1. Define the target correctly

- Precision >=80% and recall >=80% at the **same frozen operating point**, overall and separately for each advertised class.
- Detector mAP50 >=80%. Detector mAP50-95 >=80% is a separate stretch goal requiring consistently accurate boxes across IoU thresholds 0.50 through 0.95. It cannot be promised from the current dataset or by adding epochs.
- False positives and inference latency should **decrease**, not exceed 80. Compare false positives per image at matched recall; benchmark latency on the same hardware and processing scope.
- Report detector and full fusion pipeline separately. Fusion can alter decisions; it does not demonstrate improved detector mAP or recover objects never proposed.
- DEV results guide experiments. Final claims need untouched acquisition-group-disjoint evaluation with confirmed annotations; raw XTF requires its own validation.

## 2. Current baseline and saved work

`models/controlled/v8a_labels_fixed_01/weights/last.pt` preserves 60 completed epochs of 80 and optimizer state. `best.pt` is epoch 59. Backups exist under `.temp/corrected-run-checkpoint-backup-20261003`. The interruption cause is unknown. Resume only if explicitly chosen; do not rerun the fresh-training launcher against the existing run.

Measured on 1,129 corrected DEV images at 640px:

| Measurement | Result |
|---|---:|
| Validator mean-class precision / recall at its selected F1 point | 76.42% / 70.23% |
| mAP50 / mAP50-95 | 71.89% / 50.05% |
| Fixed confidence 0.25 object-micro precision / recall, IoU >=0.50 | 75.95% / 39.12% |
| TP / FP / FN at that fixed threshold | 897 / 284 / 1,396 |
| GPU detector forward mean, RTX 4060 Laptop, batch 1 FP32 | 9.92 ms/image |

Fixed-threshold per-class findings:

| Class | TRAIN boxes | DEV boxes | Precision | Recall | False positives |
|---|---:|---:|---:|---:|---:|
| crab_pot | 8,757 | 1,275 | 72.24% | 21.02% | 103 |
| submarine_pipeline | 1,000 | 147 | 99.32% | 100% | 1 |
| shipwreck | 2,011 | 544 | 62.57% | 42.10% | 137 |
| ghost_net | 765 | 135 | 98.54% | 100% | 2 |
| mine_cylinder | 1,445 | 192 | 74.21% | 61.46% | 41 |

These are inherited historically used DEV labels, not verified field truth. Excellent scores on pipeline/net DEV do not establish cross-site generalization. There are 2,675 inherited empty TRAIN labels; they require review before being called confirmed background.

## 3. Local dataset index

Counts below are file entries found recursively, not independent scenes. PNG counts may include masks and review illustrations. Revisions and crops overlap with source datasets; never sum them into a unique training count. Source licenses, semantic annotations and acquisition identity still require verification.

| Folder | Local raster/log entries | Planned use |
|---|---:|---|
| controlled_v8a_20261003 | 13,342 images: 12,213 TRAIN + 1,129 DEV | Preserve pinned baseline; 874 regenerated crops included in TRAIN |
| crab_pot | 6,674 JPG | Priority source for crab-pot annotation/scale/sequence review; deduplicate against current TRAIN/DEV first |
| AI4Shipwrecks | 537 PNG | Contains imagery/masks; pair them and inspect instance semantics before extracting boxes |
| ai4shipwreck_bbox_audit / ai4shipwreck_bbox_audit_v2 | 30 / 26 raster entries | Review artifacts; not additional independent training pools |
| China-Offshore-SSS-AI | 3,255 JPG/PNG | Native categories and source regions exist. Review class mappings and rights; do not equate pipeline/cable or fishing-net labels automatically with project classes |
| MILCONOMBO Side-Scan Sonar Mine Dataset | 1,170 JPG | Review native mine classes, annotation pairing and acquisition grouping before mapping to mine_cylinder |
| SSS_UXO | 307 JPG | Local audit found zero annotation files; annotation queue only |
| xtf | 143 XTF, approximately 18.206 GB | Raw survey domain and field workflow; label representative windows before supervised use |
| drishti_sss / v2 / v3 / v4 / v7 | 11,879 / 12,177 / 15,479 / 17,934 / 11,495 images | Derived versions with historical roles; recover lineage, do not concatenate |
| V8-A-TARGETED-HARD-POSITIVE | 12,419 images | Old faulty revision; do not train directly. 919/920 lineage-listed crops had empty loader-paired labels in prior audit |
| v3_crab_crops | 1,000 JPG | Derived crops; source-parent and full visible-box checks required |
| v3_hard_negatives / v3_normal_negatives | 392 / 750 images | Candidate negatives, not certified negatives until reviewer confirms no target |
| v4_hard_positives | 2,454 JPG | Derived positives; inspect source parent, all visible labels and historical split |
| gate_a_SOURCE_STATE_UNKNOWN and four NORMALIZED variants | 1,130 images each | Historical processing experiments, not five independent datasets; state-unknown pool excluded until resolved |
| quarantine | 1 JPG | Keep excluded until reviewed |
| baseline | No rasters, one YAML | Configuration only |

Existing AI4Shipwrecks audit processed 141 masks, 54 empty, with 647 connected components. A connected component is **not automatically a shipwreck instance**: shadows and fragmented masks need semantic inspection. Existing China audit has empty harmonized labels, so it is not ready for direct class-map conversion.

## 4. Ordered implementation and experiment phases

### M2-A: preserve the baseline and measure failures (no training)

1. Pin checkpoint/data hashes and save the interrupted-run report.
2. Cache DEV predictions at low confidence. Sweep thresholds and compare class-correct P/R at the same threshold; keep DEV threshold selection separate from final evaluation.
3. Review false positives and misses by class, target size, source, contrast and box quality. Include correct detections and random images so review is not exclusively model-selected.
4. Inspect a bounded first batch: 100 crab-pot failures, 100 shipwreck failures, 50 mine failures, plus 100 candidate backgrounds. These are review workload starting points, not sufficient final-test sample sizes.
5. Compare 640, 960 and overlapping tiles at inference only using identical scoring and duplicate merging. Measure whether resolution improves proposal recall/localization enough to justify training and extra latency.

Deliverables: error gallery, per-class PR curves, AP by object size/source, label-issue queue and latency comparison. Do not assume changing confidence can make both P and R exceed 80.

### M2-B: build one reviewed dataset revision (no training)

1. Preserve source bytes. Index license, native class, image/label hash, parent, sequence/site/survey and every historical role.
2. Deduplicate exact bytes, decoded pixels and near-identical adjacent frames. Keep all source parents/crops and related acquisition groups in the same role.
3. Keep current DEV as historical experiment data. Reserve genuinely untouched acquisition groups for final evaluation; if all available groups were already used, obtain new evidence rather than rename old TEST files.
4. Review the 141 invalid historical TRAIN annotations and mask-derived shipwreck boxes; record approved repairs in a new revision. Never automatically label an uncertain image as background.
5. Prioritize diverse small/low-contrast crab pots, precise shipwreck boxes and rock/ripple/shadow negatives. Maintain mine, pipeline and net examples to prevent regression.
6. Use controlled sampling/crops so rare difficult cases receive exposure without flooding the dataset with repeated copies. Include all visible targets in each crop; avoid introducing labelled-background false negatives.
7. Split TRAIN / DEV / calibration / final by acquisition group, not random tiles. Keep source/site strata and class support visible. Expert review is required for semantic corrections; machine predictions are suggestions only.

Deliverables: reviewed manifest/YAML, annotation overlays, class/size/source counts, exclusions and protected splits. New local folder suggestion: `datasets/reviewed_sonar_r01` (not yet created or ready).

### M2-C: finish the preserved run as a reference (optional first training)

Resume the existing run for its remaining scheduled epochs with its original data/settings. This preserves comparability; it is not the main strategy for raising mAP50-95 from 50 to 80. Re-evaluate its selected best checkpoint. Save epoch checkpoints in future experiment settings so interruptions are recoverable.

Verified Ultralytics resume form, **run by the user only if choosing this phase**:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B -c "from ultralytics import YOLO; YOLO(r'models/controlled/v8a_labels_fixed_01/weights/last.pt').train(resume=True)"
```

This resumes the target of 80 total epochs; it does not add 80 new epochs. Do not change labels while this run resumes.

### M2-D: train the reviewed detector (main training phase)

Experiment D1: existing YOLOv8s-P2 architecture, reviewed R01, 640px. Compare against the reference on the same DEV. Select starting weights only after comparing V6 and corrected candidate on the same data. Retain all five classes; do not train five unrelated classifiers as a substitute for detection.

Initial budget: up to 80 epochs with early stopping; batch chosen by measured GPU memory, not assumed. Freeze class map and log all settings. Keep epoch outputs in a new run directory. A training budget is not an expected metric.

Experiment D2, only if scale failure is demonstrated: the same architecture/data at 960px, initially batch 4 on the 8GB GPU, reduced if the memory smoke check requires it. Compare against D1 with both at matched inference settings. Keep resolution as the main changed factor.

Experiment D3, only if acoustic augmentation is justified: compare conservative gain/speckle/dropout augmentation or reduced mixup/mosaic with D2 settings. Do not apply CLAHE/denoising to all datasets without measuring target preservation. Keep matching preprocessing at training and deployment.

Optional later architecture experiment: larger P2 detector only after label/scale fixes and measured memory/latency checks. More parameters are not the first remedy for inaccurate boxes.

No exact D1/D2 launch commands are claimed ready: the reviewed dataset and launch preflight do not yet exist. Implement those phases, verify the inputs, then issue the runnable command. Do not bypass the existing guarded provenance checks to manufacture readiness.

### M2-E: train compatible fusion and calibrate

Regenerate detector-specific candidates on allowed training/calibration groups. Fit fusion using confirmed target/background candidates, compare at matched recall, and retain the detector-only baseline. Do not attach the old frozen fusion policy to a new detector without compatibility verification. Fit supported confidence calibration on a separate calibration pool and freeze class-specific operating points if evidence supports them. Scores without sufficient calibration evidence remain explicitly uncalibrated.

### M2-F: locked evaluation and deployment decision

Evaluate the frozen rendering/detector/fusion/calibration bundle on untouched groups once selection ends. Report overall and per-class P/R with uncertainty, detector mAP50/50-95, background FP/image, size/source strata, model-only and full-pipeline timings. Report every failed target honestly.

For XTF: annotate target windows and background from separate held-out survey groups, verify rendering and metadata, and measure the same release criteria. The existing XTF public gate remains 90/90 unless explicitly changed; an 80+ image DEV result does not enable it.

### M2-G: optimize speed after accuracy is demonstrated

Benchmark FP16/export options on the actual supported hardware and compare outputs against FP32. Quantization requires representative calibration and a new accuracy check. Keep CPU/cloud timings separate. Future edge endpoint availability does not establish AUV hardware performance.

## 5. Which components need training?

1. **Detection model:** priority, with reviewed five-class data; crab-pot and shipwreck failures drive enrichment.
2. **Evidence fusion:** regenerate and refit only after selecting the new detector.
3. **Confidence calibration:** fit on a separate labelled pool after detector/fusion selection.
4. **Optional segmentation model:** only if masks are sufficiently reliable and pixel-level segmentation is required. It is not necessary to replace the valid bounding-box route.

XTF parsing, navigation, record storage, report generation and the edge API do not require neural-network training.

## 6. Immediate decision

First run M2-A and M2-B. Resume the saved run if desired to complete the reference, but do not launch another long unchanged training run expecting every metric to cross 80. The first new main experiment is the reviewed five-class dataset at the existing architecture; resolution follows only when the diagnostic evidence supports it.

Documentation: https://docs.ultralytics.com/modes/train/ (resume and training options), https://docs.ultralytics.com/modes/val/ (evaluation). Use the installed package's supported options; do not upgrade it during an active run.
