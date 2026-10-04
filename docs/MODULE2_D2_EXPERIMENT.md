# M2.08 — D1 diagnosis and controlled D2 augmentation experiment

> **Submission override — 4 October 2026:** M2.08–M2.12 now follow [the deadline plan](MODULE2_SUBMISSION_PLAN.md): one short D1 fine-tune, at most one conditional second learned run, then freeze, QA and packaging. The earlier 80-epoch D2 launch is superseded; no training has been started by the agent.


4 October 2026. **Analysis, resolution probe and D2 launcher preparation completed. D2 fitting/results pending.** No training, label edits, model promotion or HF inference occurred during this phase's preparation.

## 1. What D1 established

The 80-epoch D1 model did not reach the 80/80 target. At fixed confidence 0.25, P/R was 75.97%/43.70%, with 317 FP. The preserved reference had 75.95%/39.12%, with 284 FP; mAP50 dropped from 71.89% to 70.71%. Different completed epoch budgets prevent attributing every change solely to the dataset.

The new analysis scored all 1,129 DEV images at 18 thresholds from 0.001 to 0.95. Cached low-floor predictions exactly reconciled with the prior fixed-confidence TP/FP/FN counts: 1,002/317/1,291. No prediction-cap images were present.

- **No tested confidence point meets overall 80% precision and recall together.** At 0.001, recall only reaches 70.65%, with 9.76% precision and 14,976 FP. This finite, post-NMS screen is not a proof about all possible detector settings.
- Best tested micro F1 was at 0.15: P 68.70%, R 48.06%, FP 502. It is exploratory DEV selection, not calibrated deployment confidence. No threshold was changed in production.
- Crab pots: 915 FN at 0.25; diagnostic overlap groups are 431 low-score overlaps, 449 without retained same-class overlap, and 35 localization overlaps. These are matching hypotheses, not independently verified annotation/error causes.
- Crab small-target recall: **28.21%** (352/1,248). Small shipwreck recall: **15.44%** (21/136); large shipwreck recall: 71.95% (159/221).
- Shipwreck FP: 58 localization-overlap, 15 duplicate-overlap, 23 unmatched-region. Mine/cylinder FP: 58 unmatched-region, 7 localization, 2 duplicate. An unmatched region is not proof of natural background; source labels can be incomplete.
- Filename namespace `wreckA` recalls 34.97%, `wreckR` 83.16% at the same threshold. These are filename strata, **not recovered survey/site identity**.

Automatic screening removed uncertain empty-label images. There is still no confirmed-negative training or independent target-free evaluation pool. This can contribute to false alarms; it cannot be repaired by inventing background truth.

## 2. Resolution probe before selecting D2

Same frozen D1 checkpoint, same DEV images/GT, confidence floor 0.001, NMS 0.7, max 300 detections, FP32, batch 1:

| Fixed confidence 0.25 | 640px | 960px |
|---|---:|---:|
| Overall precision | 75.97% | 63.96% |
| Overall recall | 43.70% | 42.96% |
| FP | 317 | 555 |
| Crab-pot recall | 28.24% | 26.82% |
| Shipwreck recall | 43.38% | 47.06% |
| Mine/cylinder recall | 64.58% | 54.69% |

Neither resolution reaches overall 80/80 anywhere on the tested grid. No prediction caps affected this probe. 960 increases shipwreck recall but regresses overall precision, crab recall and mine recall. Therefore **960 is not chosen as the next default or production change**. This result tests inference resolution on a 640-trained model, not a future 960-trained model; it does not prove that all resolution training is futile.

The 960 probe used serialized CUDA safety mode (`CUDA_LAUNCH_BLOCKING=1`) and one CPU thread. Its 54.37ms mean local wall time cannot be compared directly with the normal 7.43ms model-forward D1 measurement. No new mAP was claimed from this resolution probe.

Private full evidence and preview plots:

- `.temp/module2-d1-diagnosis-20261004/`: verified predictions, threshold/size/source diagnostics, 49-image gallery and PR plot.
- `.temp/module2-d1-960-probe-20261004/`: 1,129 per-image outputs, full 960 predictions, comparison and PR plot.
- Checked-in summaries under `docs/metrics/module2-d1-diagnosis-20261004.json` and `module2-d1-960-probe-20261004.json`.

## 3. Selected next experiment: D2, mosaic disabled

**One scientific change relative to D1: mosaic probability 0.8 → 0.0.** Resolution, batch, inherited dataset, starting V6-P2 weights, optimizer, seed, learning rates, mixup, scale range, other augmentation, early stopping and 80-epoch budget remain unchanged. Operational run name changes so D1 is preserved.

Hypothesis: mosaic can disrupt full-image sonar context and alter small-target presentation; removing it may improve recall/localization. The measured small-target/source mismatch justifies testing this augmentation factor. It is **not evidence that mosaic caused the failures**, and it may reduce useful variety or worsen metrics. Keeping mixup/scale unchanged deliberately isolates the mosaic change; later changes require their own comparison.

This is not a claim that another unchanged run will solve the problem. The alternative of a larger model is deferred: current evidence identifies scale/domain/annotation and negative-data issues, not proven lack of model capacity.

## 4. User training command

Run only after other training/inference jobs have stopped:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/train_module2_d2.py --execute
```

New output:

`models/controlled/m2_d2_curated_r01_mosaic0_640_01`

Uses RTX 4060 GPU 0, batch 8, 640px, up to 80 epochs, patience 20. It starts from the same V6 reference as D1; **it does not continue D1 weights**, which would add a second scientific factor. Epoch checkpoints and console logs are retained just as in D1. GPU fitting itself has not been smoke-tested by the agent.

If interrupted after a checkpoint was saved and its process has stopped:

```powershell
python -u -B scripts/train_module2_d2.py --resume --execute
```

This resumes D2 only, including optimizer state, toward the original 80 total epochs. Fresh launch refuses an existing run. Completed/stripped checkpoints and changed dataset/settings are rejected. A failure before the first checkpoint cannot be resumed; preserve its log and investigate before creating another experiment identity.

Without `--execute`, the command performs only the pinned full dataset, GPU, checkpoint/version and disk-headroom checks. No package updates or anonymous/server inference fallbacks are involved. Console logs are under `.temp/module2-training-logs`, and preflight evidence under `.temp/module2-experiments`.

## 5. Comparison and selection rules after D2

After training finishes, measure the actual D2 checkpoint, not D1:

```powershell
python -u -B scripts/evaluate_module2_d2.py --output .temp/module2-d2-evaluation-first
```

Use a new output path if that directory already exists. This evaluator uses saved D2 `best.pt` and unchanged historical DEV at the same FP32/640 protocol. It reports fixed-confidence overall and per-class P/R, mAP50/mAP50–95, FP and model-forward/local timing. The separate low-floor diagnosis should follow for matched-recall/precision comparisons and small-target strata.

Do not select D2 merely because one class or one metric increases. Compare all five classes; prioritize crab/shipwreck recall and box localization while recording mine precision and pipeline/net regressions. Compare FP at matched recall as well as at the fixed threshold. If results are mixed, report the tradeoff and retain D1 as a reference. Targets remain overall/per-class >=80% P/R at the same operating point; no successful number is promised.

If D2 regresses, do not auto-run a larger model or invent negative labels. The next data work must increase trustworthy small-target/context diversity and obtain confirmed natural-background support. Semantic uncertainty cannot be closed by a hyperparameter sweep. Older fusion/calibration remains incompatible until regenerated/verified for the selected detector.

## 6. Preparation verification and status

Nine launcher tests use mocked fitting only, including a configuration-difference check proving that only mosaic and operational run name differ from D1. Full real dataset/GPU/P2 checkpoint/disk preflight is saved separately. The analysis uses all DEV images and exactly reconciles prior fixed-confidence counts. Inference weights were hash-checked unchanged; original images/labels were not modified.

**M2.08 analysis and experiment preparation are ready; D2 training/results remain pending.** Calibration, scientific source approval, confirmed negative evidence and independent/XTF evaluation are still not certified. This phase does not unlock public XTF or guarantee 80/90% metrics.
