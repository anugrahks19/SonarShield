## M2.12 submission packaging — 4 October 2026

Judge documentation, architecture, factual results, editable deck and hashed local backup package completed and verified. See [submission scope](MODULE2_M212_SUBMISSION.md). No further training or model deployment. Independent accuracy and compatibility gates remain open. Older phase entries below are historical.

## Current status — M2.11, 4 October 2026

M2.10 completed 10/10 epochs and was measured; it did not win the final precision-floor comparison. M2.11 local release QA and detector-only freeze completed. Selected M2.08: P80.10%, R41.43%, FP236 on reused historical DEV. The 80/80 goal is unmet. Production weights remain unchanged; compatibility/calibration and real authenticated live verification are not established by this phase. See [M2.11 report](MODULE2_M211_RELEASE.md). M2.12 packaging is next; no third training run planned. Older status entries below are historical.

## Latest M2.10 status — 4 October 2026

Final short-run preparation corrects the inherited fine-tune bias warmup (0.1 versus main LR 0.0001). Starts from D1; <=10 epochs with a 45-minute epoch-boundary budget. User command: `scripts/train_module2_final.py --execute`. No training started by the agent or deployment changes. [Recipe and evidence](MODULE2_M210_FINAL_RUN.md). Training/evaluation remain pending; no third run planned.

## Latest M2.09 result — 4 October 2026

Threshold selection is complete: M2.08 DEV candidate reaches 80.10% micro precision / 41.43% recall / 236 FP at threshold 0.3653043210506439. Requiring >=80% precision per class yields 85.93% overall precision / 37.03% recall / 139 FP. The 80/80 goal remains unmet. No training, promotion or deployment. See [M2.09 report](MODULE2_M209_OPERATING_POINTS.md).

## Latest M2.08 status — 4 October 2026

The submission deadline plan supersedes historical phase numbering below. M2.08 now prepares TRAIN-only targeted sampling and a <=15-epoch D1 fine-tune. No fitting was launched. Details: [small-target preparation](MODULE2_M208_SMALL_TARGETS.md) and [M2.08–M2.12 deadline plan](MODULE2_SUBMISSION_PLAN.md). Use `scripts/train_module2_submission.py --execute`; do not use the older 80-epoch D2 command. Scientific validation and 80/80 improvement remain pending.

# Module 2: controlled route to the 90/90 goal


> **Submission override — 4 October 2026:** M2.08–M2.12 now follow [the deadline plan](MODULE2_SUBMISSION_PLAN.md): one short D1 fine-tune, at most one conditional second learned run, then freeze, QA and packaging. The earlier 80-epoch D2 launch is superseded; no training has been started by the agent.


> 80+ execution roadmap: **M2.01 Preserve and benchmark completed** on 3 October 2026. See [preserved baseline](MODULE2_BASELINE.md) and [ordered plan](MODULE2_80PLUS_PLAN.md). This closes baseline preservation only; the historical M2.01 scientific source audit below remains partial. **M2.02 failure diagnosis completed**: [report](MODULE2_DIAGNOSIS.md). **M2.03 resolution/tiling comparison completed**: [report](MODULE2_RESOLUTION.md). Keep 640 as the reference; no tested strategy meets 80/80. **M2.04 technical source audit completed**: [report](MODULE2_SOURCE_AUDIT.md). Source semantic/rights/acquisition approval remains pending. **M2.05 review workspace prepared**: [review instructions and safeguards](MODULE2_ANNOTATION_REVIEW.md). **Automatic M2.05 screening completed**: [M2.06 handoff](MODULE2_AUTOMATIC_HANDOFF.md), 9,369 eligible inherited TRAIN candidates and 2,844 exclusions. **M2.06 technical dataset build completed**: [revision, verification and M2.07 handoff](MODULE2_CURATED_DATASET.md). New revision contains 9,369 TRAIN / 1,129 historical DEV, verified copies and exploratory integrity preflight. **M2.07 D1 preparation verified**: [launch and recovery instructions](MODULE2_D1_TRAINING.md). Eight launcher tests and real dataset/GPU/checkpoint/disk preflight passed. **Update 4 October 2026: user completed D1 80/80 epochs and fresh DEV measurement passed**: [results](MODULE2_D1_RESULTS.md). At confidence 0.25: P 75.97%, R 43.70%, FP 317; mAP50 70.71%, mAP50-95 50.01%. **M2.08 D1 analysis and D2 preparation completed**: [evidence, mosaic ablation and launch](MODULE2_D2_EXPERIMENT.md). Full threshold/size diagnostics and 960 probe did not meet 80/80; 960 regressed overall. Nine D2 launcher tests and real preflight passed. D2 user training/evaluation remain pending; expert approval, confirmed negatives and independent evaluation remain unverified. No training was resumed by the agent; D1 was subsequently run by the user.

> Technical dataset correction is now prepared: [local training command, safeguards and remaining scientific gates](MODULE2_TRAINING_READY.md). The prior V8-A dataset and run are preserved; the new revision is explicitly exploratory.

Started 3 October 2026. Goal: class-correct object precision >=90% **and** recall >=90% at the same frozen operating point on independently labelled data. This is a target, not a guarantee or a system-accuracy percentage. An image-only validation result cannot certify raw XTF performance.

> Phase numbering: the current 80+ sequence uses M2.07 for D1 training and M2.08 for controlled variants. The historical 90/90 list below uses earlier numbering and is retained as context, not the current execution order.

## Current findings: M2.01 kickoff

The read-only audit inventoried 27,880 image entries in V8-A TRAIN and Drishti V3 TRAIN, val_clean, val, test and benchmark_bg. Counts include images reused between revisions; this is not 27,880 independent scenes. Full image hashes, label hashes/errors and crop lineage were saved privately under `.temp/module2-kickoff-audit-20261003`. Checked-in [summary evidence](metrics/module2-kickoff-audit-20261003.json) records exact identities and scope.

- V8-A: 12,401 training images. **919 of 920 lineage-listed hard-positive crops have empty labels in the current on-disk revision.** An empty YOLO detection label represents background to the loader, so this revision is unsuitable as a hard-positive enrichment without repair. This audit does not establish what an earlier run loaded from a cache or a different revision.
- V8-A and Drishti V3 TRAIN each have 141 files with boxes outside the original normalized raster boundary or otherwise failing the declared label check. These must be reviewed; clipping or deleting labels automatically is not a semantic correction.
- There are 1,318 exact-byte cross-role hash groups. Most are expected-to-be-related historical aliases: 995 DEV_CANDIDATE/HISTORICAL_VALIDATION, 322 HISTORICAL_BACKGROUND/HISTORICAL_VALIDATION and one HISTORICAL_BACKGROUND/HISTORICAL_VALIDATION/TRAIN. Do not describe all 1,318 as training/test leakage; the one TRAIN overlap must be excluded from independent background evidence.
- All 920 recorded crop parents were found by source hash in the inventoried pools; no recorded crop parent was found in DEV/test while its crop was in TRAIN. This limited exact-hash check does not certify site/mission independence or absence of near duplicates.
- Current V8-A YAML uses `drishti_sss_v3/test/images` as training validation. Its saved args reference that YAML. Preserve V8-A as test-informed exploratory work; those test data cannot become a fresh final holdout by renaming them.
- The raw XTF review pack has 162 unreviewed windows and no confirmed target labels. It stays excluded from training and final accuracy claims until independently reviewed.

No training, inference, relabeling, moving, deleting or model promotion occurred in this kickoff. The deployed V6-based detector remains unchanged. Existing crop/source licenses, human annotation quality, acquisition groups, near duplicates and pretraining/selection history still require review; M2.01 is **partially complete**, not signed off.

## Ordered next work

```mermaid
flowchart LR
 A[M2.01: lineage, labels and leakage audit] --> B[M2.02: protected splits and evaluation rules]
 B --> C[M2.03: comparable DEV baselines]
 C --> D[M2.04: corrected and reviewed targeted data]
 D --> E[M2.05: one controlled detector experiment]
 E --> F[M2.06: compatible evidence fusion]
 F --> G[M2.07: calibration and frozen operating point]
 G --> H[M2.08: untouched external evaluation]
 H --> I[M2.10: reviewed promotion and public XTF integration]
```

1. Complete M2.01 by reviewing erroneous labels and crop geometry/parent boxes, source rights, ever-used roles and acquisition identity. Preserve existing pools and outputs. Any repairs belong in a **new dataset revision** with before/after hashes and reviewed reasons, not the active V8-A folder. Do not automatically create a negative for an uncertain or missing annotation.
2. M2.02 freezes train/DEV/CALIB/final roles and evaluator definitions. Final data must be group-disjoint, independently labelled and sufficiently cover all advertised classes. Exclude known training duplicates and previously test-informed evaluation pools from final evidence. Unknown provenance stays unknown.
3. M2.03 compares the frozen V6 and available exploratory candidates only on permitted DEV data with identical processing. Diagnose misses, wrong classes, natural-background false alarms and small-object/scale failures. Existing metrics from different splits are not a fair leaderboard.
4. M2.04 fixes the documented crop-label defect and boundary errors in reviewed new revisions, then adds real difficult positives and confirmed natural negatives. New sonar gain/noise/scale augmentations must preserve valid boxes and be justified by DEV failures. XTF-derived positives need expert labels, not model pseudo-truth.
5. M2.05 changes one major factor per experiment. Corrected-label fine-tuning comes before speculative model enlargement. Resolution/tiling/sampling experiments follow only if measured failures justify them. Training is launched by the user, never automatically by this agent.
6. M2.06 regenerates compatible evidence for the selected detector and evaluates fusion at matched recall; it cannot recover targets that were never proposed. M2.07 fits supported calibration on CALIB and freezes the complete bundle. Unsupported classes stay explicitly uncalibrated.
7. M2.08 evaluates once the pipeline and untouched external set are locked. Report precision, recall, mAP50/50-95, each class, background false alarms, acquisition strata and uncertainty; model optimization, if needed, precedes this gate. A failed goal remains a failed result, not a reason to reinterpret the holdout as DEV without reserving new evidence.
8. Passing the reviewed [XTF release criteria](XTF_ACCURACY_RELEASE.md) makes public integration eligible. M2.10 then packages the verified rendering/model/fusion/calibration bundle, preserves rollback, and runs public upload-to-report checks. Passing accuracy numbers alone does not automatically deploy a backend or establish geographic correctness.

## Commands now versus later

Audit only, using a fresh output directory:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -B scripts/audit_module2_data.py --output .temp/module2-audit-next
```

**Do not relaunch `ai/train_v8_a.py` with its current YAML.** No replacement dataset is approved yet. After review, a new `datasets/approved_sonar/data.yaml` and `split-manifest.csv` must contain the actual separate TRAIN/DEV image paths, hashes, verified labels and acquisition groups; those paths are prerequisites, not currently populated training data.

```powershell
python -B scripts/train_guarded.py --data datasets/approved_sonar/data.yaml --manifest datasets/approved_sonar/split-manifest.csv --weights models/v6/detector_v6_p2_sss/weights/best.pt --dry-run
```

Only after this preflight and the provenance/evaluation gates pass, the user can launch a bounded experiment:

```powershell
python -B scripts/train_guarded.py --data datasets/approved_sonar/data.yaml --manifest datasets/approved_sonar/split-manifest.csv --weights models/v6/detector_v6_p2_sss/weights/best.pt --epochs 80 --device 0 --project models/controlled --name reviewed_candidate_01 --execute
```

80 epochs is an initial experiment setting, not a promise of 90/90. Threshold tuning alone commonly trades precision against recall; both must meet the goal together. Existing frozen scores remain uncalibrated until supported calibration is produced.
