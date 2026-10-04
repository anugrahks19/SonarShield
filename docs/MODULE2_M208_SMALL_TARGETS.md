# M2.08: submission small-target fine-tune

Prepared 4 October 2026 in `E:\GITHUB\a sih 2026`. Training is user-launched. Preparation is verified; trained accuracy is pending.

## Why this experiment

D1 fixed-confidence DEV performance: precision 75.97%, recall 43.70%, mAP50 70.71%, mAP50–95 50.01%, 317 false positives. Confidence-only tuning did not reach 80/80. The 960 inference probe increased false positives and did not improve overall recall. Small crab pots and small/medium shipwrecks are priority misses.

Crab-pot box sizes differ markedly: about 27.7% of TRAIN boxes are small at 640 letterbox, compared with about 97.9% of DEV boxes. This motivates an exploratory sampling intervention, not proof of why every miss occurs.

## Recipe

- Start from D1 best.pt, SHA256 `fde6a1e39e927b4f8908b389d73d9ba753435ac53cbad56eb2443c73d3888cef`.
- Same P2 detector, 640 input, batch 8, AdamW initial LR 0.0001, <=15 epochs, patience 5.
- 75-minute budget checked after a saved epoch; initialization, current epoch and final validation add time. Preserve four hours before submission for evaluation and packaging.
- No mosaic or MixUp; reduce scale augmentation from 0.5 to 0.2 and translation from 0.1 to 0.05 to reduce shrinking, clipping and blended acoustic evidence. These are hypotheses, not measured improvements.
- Keep all existing complete image/label pairs and their context. No new crop, label, background or pseudo-label is invented.
- Sample 9,369 TRAIN draws per epoch with replacement. Forty percent probability mass is uniform across all TRAIN images. The remaining mixture is 25% small crab, 15% small/medium wreck, 10% mine, 5% pipeline and 5% net. Images may belong to multiple groups; group contributions are summed.
- Small means box area <32² pixels; small/medium wreck means <96² at 640 letterbox. These are image-space buckets, not physical dimensions.
- DEV remains all 1,129 original images, with normal sequential validation. No DEV image enters the TRAIN sampler. DEV statistics motivated the recipe, so DEV is exploratory and cannot be called an untouched test.

| Image bucket | Uniform expected draws/epoch | Targeted expected draws/epoch | Exposure ratio |
|---|---:|---:|---:|
| Small crab | 1,619 | 2,989.85 | 1.85× |
| Small/medium wreck | 477 | 1,596.15 | 3.35× |
| Mine | 873 | 1,286.10 | 1.47× |
| Pipeline | 1,000 | 868.45 | 0.87× |
| Net | 765 | 774.45 | 1.01× |

Expectations are before augmentation, not actual draw counts or extra independent data. Large/non-targeted images retain positive uniform probability but are sampled less frequently. Pipeline regression must be checked. Resampling cannot manufacture missing target domains or confirmed natural-background negatives.

## Immutable identities and implementation

Dataset manifest SHA256: `f2f8fff98d631725cd3066726056943bc9b2910abce49a380cc6521f7205f796`.

TRAIN sampler artifact: `.temp/module2-experiments/m2-smalltarget-sampling-20261004-r02.json`, SHA256 `08dd6e21a304348d5636444c470bba366617ebb55813618753217dcd3c60f799`.

Output: `models/controlled/m2_submission_ft15_smalltargets_01`. Older checkpoints and deployed artifacts are preserved. The superseded preparation artifact r01 is retained as history and is not used by the launcher.

`module2_targeted_sampling.py` constructs weights from existing TRAIN labels and dimensions. The custom trainer aligns weights by resolved path, refuses missing/extra/duplicate paths, rejects DDP and nonzero worker configurations, and uses an epoch-seeded sampler. Validation delegates to the installed Ultralytics trainer. The sampler reproduces the same draw sequence at a resumed epoch; this does not promise bitwise reproduction of every CUDA operation or augmentation after an interruption.

The launcher pins the sampling artifact, dataset and starting checkpoint, refuses an existing fresh run and saves checkpoints each epoch. Resume verifies the same recorded sampling identity and settings. Recorded training time carries across resume; abrupt interruption can lose timing within an unfinished epoch. Completed/stripped checkpoints cannot be resumed into more training.

This is a deadline intervention with multiple changes, not an isolated scientific ablation.

## Commands

Start only when enough submission margin remains:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/train_module2_submission.py --execute
```

After an interruption, once the original process has stopped:

```powershell
python -u -B scripts/train_module2_submission.py --resume --execute
```

After completion:

```powershell
python -u -B scripts/evaluate_module2_submission.py --output .temp/module2-submission-smalltargets-eval
```

The evaluator records fixed 0.25 micro precision/recall, mAP50/95, false positives, per-class results and FP32 batch-1 timing. M2.09 compares operating thresholds and checkpoints before selecting a model. Validator mean-class P/R and fixed-threshold micro P/R must not be mixed.

## Verification performed

- Five launcher tests: settings, overwrite prevention, D1 initialization, budget callback and completed-resume rejection.
- Five sampling tests: letterbox-size classification, normalized positive weights, required groups, path alignment/DEV rejection, and deterministic epoch sampling/resume plus validation delegation/tamper rejection.
- Full preflight: hashes, 10,498 image/label/source pairs, split/parent identities, class map, package versions, GPU and P2 strides.
- Real CPU TRAIN loader batch: shape 8×3×640×640, 15 valid transformed boxes; 9,369 images / 1,172 batches per epoch. Real DEV loader: 1,129 images, sequential sampler, one batch loaded. No model forward/backward or fitting.
- No agent-launched training, no model promotion, no HF inference calls or deployment.

Evidence: `docs/metrics/module2-m208-smalltargets-preparation-20261004.json`.

## Accuracy gate

Goal: >=80% precision and >=80% recall at the same operating point, with per-class disclosure. No measured improvement is claimed yet. Keep D1 if the candidate regresses. mAP50 >=80% is a target; mAP50–95 >=80% is a stretch goal. Missing calibration, real-net labels, confirmed negatives and independent XTF ground truth remain unresolved. Public XTF stays gated.
