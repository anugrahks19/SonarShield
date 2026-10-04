## M2.12 submission packaging — 4 October 2026

Judge documentation, architecture, factual results, editable deck and hashed local backup package completed and verified. See [submission scope](MODULE2_M212_SUBMISSION.md). No further training or model deployment. Independent accuracy and compatibility gates remain open. Older phase entries below are historical.

# Submission plan: M2.08–M2.12

Revised 4 October 2026 for submission **5 October 2026 (Asia/Calcutta)**. Exact submission hour is unknown. This plan supersedes the full 80-epoch D2 instructions and open-ended training experiments.

## Budget and freeze rule

**One short detector fine-tune recommended; at most one optional second learned run. No automatic fitting by the agent.** Count fusion or calibration fitting as learned runs too: they are not a hidden extra budget. Do not run the old 80-epoch D2 command. There is no mandatory second run, architecture search, full 960 training, segmentation training, pseudo-labelling campaign, or large-model upgrade before submission.

Reserve at least **four hours before your actual deadline** for evaluation, deployment checks, report/export tests and packaging. At that cutoff stop experiments and use the best previously verified bundle. If there is insufficient time for those four hours plus training/evaluation, skip training altogether. A recorded limitation is preferable to an untested release.

## Revised ordered phases

| Phase | Submission work | Training allowance | Completion gate |
|---|---|---|---|
| **M2.08** | Prepare TRAIN-only small-target sampling; one bounded fine-tune and compare against D1 | Default <=15 epochs; 75-minute epoch-boundary budget | Saved metrics and explicit candidate selection; no blind promotion |
| **M2.09** | Compare checkpoints and operating thresholds on unchanged DEV; check per-class precision/recall and FP | **No fitting planned** | Best measured same-threshold P/R trade-off, with per-class regressions disclosed |
| **M2.10** | Conditional second focused fine-tune, only if justified and time remains | Optional <=10 epochs / 45-minute epoch-boundary budget | Candidate retained only after comparison; otherwise keep the better existing checkpoint |
| **M2.11** | Compatibility, freeze, final same-protocol measurements and software release checks | **No fitting** | Overall/per-class P/R at the same point, mAP50/95, FP, latency; live/error/example and report/review flows checked as available |
| **M2.12** | README/PPT evidence, judge walkthrough, demo/offline backup, rollback and submission bundle | **No fitting** | Working tested entry point, correctly labelled examples, exports, artifact inventory and limitations |

## M2.08 first run: deadline fine-tune

Starting from **D1's selected saved checkpoint**, not V6 from scratch:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -u -B scripts/train_module2_submission.py --execute
```

Output: `models/controlled/m2_submission_ft15_smalltargets_01`.

- Same pinned 9,369 TRAIN / 1,129 historical DEV, P2 architecture, 640px and batch 8. TRAIN uses weighted sampling with replacement for 9,369 draws/epoch, not additional independent images; DEV uses its normal loader.
- **At most 15 additional epochs**, initial learning rate 0.0001, mosaic disabled, patience 5. MixUp disabled, geometric scale reduced from 0.5 to 0.2 and translation from 0.1 to 0.05. Other settings retained. Existing complete image/label pairs are resampled; no new crops or labels are created.
- Stops at a completed/saved epoch once its recorded training time reaches **75 minutes**. Preflight, the current epoch, final validation and cleanup add time; this is **not a hard 75-minute wall-clock guarantee**. Budget checkpoints persist recorded elapsed training across resume; an abrupt crash can leave unrecorded time within the unfinished epoch.
- Checkpoints saved every epoch, console log retained; D1 and the deployed model preserved.
- Multiple intentional changes (initialization, shorter schedule, learning rate, mosaic, sampling and geometry/MixUp): **deadline recovery experiment, not an isolated scientific ablation**. Its scientific control is weaker than the archived D2 plan.

Measured D1 took 22,527.8 seconds (~6h15m) for 80 epochs. Its average ~4.7 minutes/epoch suggests ~70 minutes for 15 epochs, but laptop load, thermals and setup can change this. This is an estimate, not a promise.

If interrupted after a saved checkpoint, with the process stopped:

```powershell
python -u -B scripts/train_module2_submission.py --resume --execute
```

Resume applies to this short run only. Completed/optimizer-stripped runs cannot be resumed into more training. Fresh launch never overwrites an existing run. Do not repeatedly restart to evade the submission cutoff. M2.10 now prepares a separate final command; neither command starts automatically.

After it finishes:

```powershell
python -u -B scripts/evaluate_module2_submission.py --output .temp/module2-submission-evaluation-first
```

## M2.10 optional second run: conditional, not required

Use the second slot only if the first evaluation identifies a specific remaining failure, a concrete change is justified and enough time remains before the four-hour freeze cutoff. Maximum proposed allowance: **10 epochs and a 45-minute epoch-boundary budget**. Prepare its exact checkpoint/configuration only after the first result; there is no automatic chain and no promise that it will help. If the first run does not improve the desired tradeoff, keeping D1 may be the better submission choice.

## Selection rules

Measure on the unchanged historical DEV using the existing FP32/640 evaluator. Keep fixed-confidence P/R and validator mean-class P/R distinct. Compare per-class support, mAP50/95, FP at matched recall, and latency. Do not choose a model just because one percentage goes up. Record any regressions and training-budget differences. Retain rollback if the candidate is mixed or unstable.

D1 reference: P 75.97%, R 43.70% at confidence 0.25; mAP50 70.71%, mAP50–95 50.01%; 317 FP; 7.43ms batch-1 model forward on this laptop GPU. The 960 probe regressed overall; confidence tuning alone did not meet 80/80. Native-net/XTF labels, confirmed negatives and field accuracy remain unresolved. Short fine-tuning cannot guarantee 80/90% metrics or repair missing ground truth.

## Submission scope and honest claims

- Maintain the current verified deployment until a replacement bundle's compatibility and integrated behavior are actually checked. A local candidate result is not evidence of production deployment.
- Keep live Hugging Face inference best effort, account quota/reachability separate, manual retries, explicit precomputed examples, and no automatic inference calls during example walkthroughs.
- Keep human review, cloud records/history, report/export and source labels in the final walkthrough. Record any hosted checks that cannot be completed by the deadline.
- Keep unsupported score calibration explicitly unavailable. A tuned DEV threshold is not a calibrated confidence estimate. Do not claim 90% accuracy from mAP or synthetic-net results.
- Public XTF stays gated: no verified labelled independent XTF evaluation exists. Show the local raw-survey prototype with its limitations if needed; do not call it validated field inference.
- Exact field geolocation/dimensions, corrected motion, hardware/AUV equivalence and independent site generalization remain unverified where evidence is missing. Do not manufacture completion to meet the deadline.

## Deliverables by phase

**M2.08:** pinned TRAIN sampling artifact, loader/unit tests, bounded user-launched training and post-run evaluation. Preparation is complete; training/accuracy are pending.

**M2.09:** same-protocol checkpoint/threshold comparison, per-class P/R and FP, selected operating settings. Do not use separate thresholds to claim overall 80/80.

**M2.10:** at most one conditional second run, <=10 epochs / 45-minute epoch-boundary budget, based on first-run measured failures. Skip if time is short or benefit is unsupported.

**M2.11:** artifact compatibility and frozen manifest; six requested metrics and browser analysis → selection → review → report/export checks. Missing calibration remains unavailable; incompatible fusion must not be reused.

**M2.12:** README/architecture/data-flow diagrams, factual results, targets labelled as targets, demo narrative, labelled examples, submission checklist and rollback bundle.

## Current status

M2.08, M2.09 and M2.10 training/measurement/selection work is complete. M2.11 local release QA and experimental detector freeze is complete: M2.08 gives the highest recall at global precision >=80% (80.10% precision, 41.43% recall, 236 FP). Neither 80/80 nor independent XTF accuracy is established. Current website model remains unchanged; new weights have no verified compatible fusion/calibration bundle.

47 frontend tests, 52 backend tests, four freeze tests, 12 metric reconciliations, release build/secret scan, local SQL regressions and five browser scenarios passed. Real authenticated HF and signed-in cloud checks were not repeated this phase. See [full release scope](MODULE2_M211_RELEASE.md). **M2.12 submission packaging remains next. No third learned run is planned.**
