# M2.07 — Controlled D1 training preparation

> Update 4 October 2026: the user completed 80/80 epochs; [fresh DEV measurements](MODULE2_D1_RESULTS.md) are saved. The instructions below record preparation and recovery behavior.

Prepared 3 October 2026. **Launcher and non-training preflight verified. Training and post-training evaluation are still pending.** This is an exploratory experiment using inherited labels, not a scientifically approved release.

## Start D1 yourself

Run in PowerShell, with no other model training running:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/train_module2_d1.py --execute
```

This is a **new experiment**, not continuation of the older 60-epoch reference. It uses your RTX 4060 Laptop GPU, up to 80 epochs, batch 8, 640px, Windows workers 0 and early stopping patience 20. Keep the terminal open. It prints four preflight stages before the epoch table; the 10,498-record identity check can take a minute. Do not start a second copy while the first is checking or training.

Output:

`E:\GITHUB\a sih 2026\models\controlled\m2_d1_curated_r01_640_01`

Console logs:

`E:\GITHUB\a sih 2026\.temp\module2-training-logs`

Saved experiment configuration/preflight:

`E:\GITHUB\a sih 2026\.temp\module2-experiments`

The original run `v8a_labels_fixed_01` remains separate. No deployed model is automatically replaced.

## If this D1 run is interrupted

After confirming its process has stopped:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/train_module2_d1.py --resume --execute
```

This resumes **only this D1 run**, preserving its scheduled total of 80 epochs and checkpoint optimizer state. It does not add another 80 epochs and cannot resume the older baseline. The launcher verifies dataset/configuration identity, original class IDs, saved epoch, optimizer presence and model architecture before resuming.

`last.pt` and `best.pt` are saved through the installed trainer, plus an epoch checkpoint every epoch (`save_period=1`). Checkpoints provide recovery at completed save points; they cannot preserve an unfinished batch or unsaved first epoch. A crash before the first checkpoint cannot be resumed with this command. Completed/optimizer-stripped checkpoints are rejected instead of silently restarting training. Existing run directories are never reused for fresh training.

No package installations or upgrades are performed. If versions change or GPU/dataset checks fail, the launcher stops. Its log includes terminal output and the bounded failure reason. It does not claim to fix previous native CUDA/Python crashes.

## What changes in D1

The main changed factor is the screened dataset: 9,369 TRAIN positives and 1,129 unchanged historical DEV images. Initial weights are the pinned V6-P2 checkpoint, matching the original baseline's initialization. This choice maintains the reference setup; it is not a claim that V6 outperforms the interrupted candidate.

Retained reference training settings: AdamW, lr0 0.001, lrf 0.01, seed 0, deterministic setting, 640px, batch 8, scale 0.5, mosaic 0.8, mixup 0.1, close mosaic 10, 5-degree rotation, no hue/saturation/value augmentation. Recovery/logging changes do not alter the intended loss or sampling distribution. Deterministic settings do not guarantee bitwise-identical GPU results across environments.

No new resampling, resolution change, mask conversion, denoising, pseudo-labels or native-category mapping is mixed into D1. The small-target mismatch is explicitly reserved for the separately measured M2.08 experiment: only 27.7% of TRAIN crab boxes are small at 640 letterbox scale, versus 97.9% of DEV crab boxes. Enlarged hard-positive crops are not automatically a solution.

## Important limitations

- TRAIN is positive-only: no confirmed natural-background pool. Removing uncertain empty labels may avoid wrong supervision but can worsen false positives. D1 is an experiment, not an assured improvement.
- Labels remain inherited; missing objects, actual acquisition groups and source rights are not fully verified. No expert-verification status was fabricated and the strict human-verified training guard was not modified.
- Ghost-net data remains synthetic; real-net and raw-XTF accuracy are not established.
- DEV has already been used for selection. It is not an independent final test or calibration pool.
- The interrupted reference completed 60 epochs. Compare budgets explicitly; an 80-epoch D1 versus a 60-epoch reference does not isolate dataset effects at equal completed training budget. Saved epoch checkpoints help later comparisons.
- There is no promised 80% or 90% precision/recall or mAP result. Public XTF stays disabled until the independent release gate passes.

## Verification performed before giving the command

- Installed versions pinned: Ultralytics 8.4.163, Torch 2.4.1+cu121, NumPy 1.26.4 and PyYAML 6.0.1.
- Actual CUDA device detected: NVIDIA GeForce RTX 4060 Laptop GPU. No forward/backward training smoke test was run.
- Starting checkpoint inspected on CPU: canonical five-class names and P2 strides 4/8/16/32.
- Full M2.06 copy/label/parent preflight passed; exact manifest and YAML hashes pinned in the launcher.
- Disk-headroom guard added for up to 80 per-epoch checkpoints plus recovery margin. The estimate is conservative and is checked again on launch; disk usage by other applications can still change afterward.
- Eight tests passed using mocked fitting only: fresh-run overwrite prevention, missing resume rejection, configuration pins, optimizer/epoch checks, separate fresh/resume dispatch, class-map guard, recovery settings and persisted callback state/path checks.
- No training, inference, HF calls, environment upgrades or checkpoint replacement occurred during preparation.

## After training

Keep the run's `results.csv`, `args.yaml`, `m2-experiment.json` and weights. Evaluate the selected checkpoint on unchanged DEV with the same 640/FP32 matching protocol: overall/per-class precision and recall at the same confidence, threshold sweep, mAP50, mAP50–95, false positives and latency. Training's mean validation P/R may use a different operating point than the fixed-confidence object metrics; do not substitute one for the other.

Do not use the old hard-coded `evaluate_interrupted_run.py` command as a D1 evaluator: it points to the older reference. Ask to measure this D1 run when it finishes, before selecting M2.08 changes. Never automatically attach the frozen old fusion/calibration policy or publish D1 based solely on DEV numbers.

**M2.07 preparation is ready. M2.07 training/results are not complete until the user runs the experiment and its saved results are evaluated.**
