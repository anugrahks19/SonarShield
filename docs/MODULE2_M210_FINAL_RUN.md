# M2.10: final short run with bounded bias warmup

Prepared 4 October 2026 for submission 5 October. This is the second and final user-launched detector run in the deadline plan. No agent-launched training or deployment.

## Concrete reason to use the remaining slot

The M2.08 recipe set `lr0=0.0001` but inherited Ultralytics `warmup_bias_lr=0.1` for three warmup epochs. Installed trainer source interpolates the bias optimizer group's learning rate from that warmup value to the scheduled main rate.

The completed run confirms this was active:

| Evidence | Value |
|---|---:|
| Main initial rate | 0.0001 |
| Default bias warmup start | 0.1 |
| Warmup/main starting-rate ratio | 1,000× |
| Epoch 1 recorded bias-group rate | 0.0667284 |
| Epoch 2 recorded bias-group rate | 0.033424 |
| Warmup duration | 3 epochs |

M2.08's first-epoch mAP50 fell to 66.53%; its later best full evaluation remained below D1 on mAP. The excessive bias warmup is a concrete configuration mismatch worth correcting. It is **not proven to be the sole cause** of the regressions, and fixing it does not guarantee 80/80.

The M2.08 preflight missed this inherited default. Existing artifacts and results are preserved, not revised to hide it.

## Final experiment

- Start afresh from **D1 best.pt**, not the potentially affected M2.08 checkpoint. Initialization SHA256 `fde6a1e39e927b4f8908b389d73d9ba753435ac53cbad56eb2443c73d3888cef`.
- Set **bias warmup start to 0.0001**, matching the main LR, and warmup duration to **1 epoch**.
- <=10 epochs, patience 5, **45-minute budget checked at saved epoch boundaries**. Preflight, the current epoch and final validation add time; this is not a hard total wall-clock limit.
- Retain the M2.08 TRAIN sampler, 640 P2 detector, batch 8, AdamW, main LR 0.0001, final LR fraction 0.01, no mosaic/MixUp, scale 0.2 and translation 0.05.
- Same pinned 9,369 TRAIN / 1,129 historical DEV. No new labels, automatic background images, crops or protected-role changes.
- Run directory `models/controlled/m2_submission_ft10_warmupfix_02`; refuse fresh overwrite. Preserve D1, M2.08 and the public backend.
- This changes the warmup recipe and shortens the schedule relative to M2.08; it is a deadline comparison, not an isolated single-factor scientific ablation.

No third training run is planned. If enough time does not remain for training/evaluation **plus four hours for release work**, skip this experiment and continue with the existing measured candidates.

## Start command

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/train_module2_final.py --execute
```

Preflight only: omit `--execute`.

If interrupted after a saved checkpoint, wait for the original process to stop, then:

```powershell
python -u -B scripts/train_module2_final.py --resume --execute
```

Completed/stripped checkpoints cannot be resumed into extra epochs. Resume verifies dataset, sampler and resolved experiment settings, including the warmup values. Budget timing persists across resume; unfinished-epoch timing can be lost on abrupt interruption. The final-validator callback does not add a phantom epoch to the budget record.

## Measure after completion

```powershell
python -u -B scripts/evaluate_module2_final.py --output .temp/module2-final-warmupfix-eval
```

This measures the same six metrics and per-class results at confidence 0.25 / matching IoU >=0.50, plus full-validation mAP and FP32 local timing. A later operating-point comparison must use the same confidence-floor/NMS/matching protocol as M2.09 before claiming a precision-floor improvement.

## Selection gate

Compare three preserved candidates: D1, M2.08 and this final run. Prefer the best measured precision/recall trade-off at the same objective, report per-class regressions, and retain rollback. No automatic checkpoint promotion or modification of frozen policy/calibration.

Current reference points:

| Candidate | Precision at 0.25 | Recall at 0.25 | mAP50 | mAP50–95 | FP at 0.25 |
|---|---:|---:|---:|---:|---:|
| D1 | 75.97% | 43.70% | 70.71% | 50.01% | 317 |
| M2.08 | 75.57% | 44.66% | 69.90% | 49.73% | 331 |

M2.09 global precision-floor candidate: M2.08 at 0.3653043210506439 gives 80.10% precision / 41.43% recall / 236 FP. It does not meet 80/80. Neither cached proposal pool reached 80% recall even at confidence floor 0.001, so threshold changes alone cannot close the gap.

## Verification and remaining work

Five mock-only launcher tests cover bounded settings/warmup, overwrite rejection, D1 initialization, the 45-minute stop/final-validation guard, and completed-resume rejection. The launcher also checks every dataset/source pair, classes, package versions, CUDA, P2 strides, sampler identity and checkpoint hash. No model fitting is needed for these checks.

Evidence: `docs/metrics/module2-m210-preparation-20261004.json`.

M2.10 preparation being ready does not mean training or accuracy selection is complete. After the user runs it, measure and compare before M2.11 freezes compatible artifacts and tests the release. M2.12 packages factual metrics, diagrams, demo/backup and limitations. Missing calibration, real-net/negative labels and independent XTF ground truth remain unavailable; public XTF stays gated.
