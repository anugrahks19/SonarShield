# M2.11: selection, freeze and release verification

Completed 4 October 2026. **Local software QA and experimental detector freeze are complete. No training, model deployment or Git push occurred in this phase.** The 80% precision / 80% recall goal remains unmet.

## Final operating-point comparison

All models use the same 1,129-image / 2,293-object historical DEV, FP32, 640, batch 1, standard detection, NMS IoU 0.7 and class-correct matching at IoU 0.5. Threshold selection maximizes recall subject to global micro precision >=80%; it does not require every class to reach 80% precision. DEV has been reused for model and threshold selection and is not an independent final test. Net examples in this pool are synthetic.

| Model | Selected threshold | Precision | Recall | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| D1 | 0.3424893022 | 80.07% | 40.12% | 920 | 229 | 1,373 |
| **M2.08** | **0.3653043211** | **80.10%** | **41.43%** | **950** | **236** | **1,343** |
| M2.10 | 0.3348314166 | 80.03% | 40.38% | 926 | 231 | 1,367 |

M2.08 wins this precision-floor objective. D1 has the highest mAP among these candidates. No model reaches 80/80 within its retained confidence-floor cache. Twelve direct greedy-matcher comparisons passed. See [selection evidence](metrics/module2-m211-selection-20261004.json) for curves, exact thresholds and per-class results.

## Six requested measurements for selected M2.08

| Measurement | Result | Scope |
|---|---:|---|
| Precision | 80.10% | Selected global threshold |
| Recall | 41.43% | Same threshold |
| mAP50 | 69.90% | Standard validator; confidence sweep |
| mAP50-95 | 49.73% | Standard validator; confidence/IoU sweep |
| Inference time | 7.53 ms | Warm batch-1 model forward, RTX 4060, FP32/640 |
| False positives | 236 | Selected threshold, this DEV pool |

Timing comes from the prior M2.08 measurement; it was not rebenchmarked at the selected filter. Local measured wall time was 10.92 ms; neither time includes remote upload, queueing or full evidence fusion. At fixed confidence 0.25 this model instead measured P75.57%, R44.66%, FP331. These detector numbers do not describe the current website's V6 global+tiled runtime or calibrated probability of correctness.

## Frozen artifacts and compatibility

Local bundle: `models/submission/m211_detector_only_20261004/` contains `candidate.pt`, `rollback-d1.pt`, `manifest.json` and `README.txt`. Candidate SHA256: `0e8767f1424e3338d3d092235d24093a3a540f54d51389ddd42c0605e01c36c0`. Both copied checkpoint hashes were rechecked. D1 is an experimental baseline backup, not a production rollback.

Class IDs and P2 strides were verified for all three candidates. The manifest pins exact threshold comparison (`>=`), packages, source hashes and inference protocol. Existing fusion/policy/calibration artifacts do not establish compatibility with these weights. They are excluded from this detector-only bundle. Decisions remain **REVIEW_ONLY**, automatic confirmation is disabled and calibrated correctness probabilities remain unavailable. Current production/runtime files were preserved. [Trackable manifest](metrics/module2-m211-frozen-manifest-20261004.json).

## Release verification

- 47 frontend tests, 52 backend tests, four freeze safeguard tests and 12 metric reconciliations passed.
- Frontend lint, typecheck, production release build and credential scan passed; local Supabase SQL regressions passed.
- Required geographiclib and pyxtf were installed into an isolated QA target. The training environment was not upgraded.
- Real headless Edge walkthroughs passed on local production preview and public Vercel with HF traffic blocked: uploaded image retained, explicit offline fallback/confirmation, candidate selection, saved review, refresh/restore, complete-record export/import, report JSON/CSV source labels and print source label. Mobile document overflow checks passed; this is not a comprehensive mobile visual certification.
- Three fully mocked browser gateway scenarios passed: authenticated-success contract/rendering, quota countdown and quota without countdown. Examples made zero additional inference calls. Mock success is not real live-inference verification.
- No real HF inference calls or quota were consumed. Isolated browser contexts did not repeat signed-in cloud checks or write cloud records.

[Consolidated verification evidence](metrics/module2-m211-release-20261004.json). Raw browser exports/screenshots are retained locally under `.temp/module2-m211-browser-20261004/` and `.temp/module2-m211-gateway-browser-20261004/`.

## Remaining release boundaries

Real authenticated HF success and signed-in cloud behavior were not freshly verified in this phase. Earlier user evidence confirmed cloud review-note restoration, five hosted admission SQL checks and maintenance HTTP200; HTTP200 alone does not establish actual expired Storage-object deletion. Independent labelled XTF accuracy, field geolocation/motion correctness and actual AUV/edge hardware equivalence remain unverified. Public XTF stays disabled. Do not promote this candidate with incompatible fusion or present DEV threshold precision as system accuracy.

**Next: M2.12 factual submission packaging and judge walkthrough. No third training run is planned.**
