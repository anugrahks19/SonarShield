# SONAR-SHIELD implementation roadmap

Date: 2 October 2026. Status: planned; creating this document does not implement any phase.

## Purpose and authority

Close the known PS 26057 defects and capability gaps in small, ordered tasks. Module 1 covers software and deterministic processing without fitting model parameters. Module 2 covers data, learned models, calibration, and independent performance evidence.

Canonical implementation checkout: `E:\GITHUB\a sih 2026`; frontend: its `frontend` directory. The older Codex worktree must not replace current repository files wholesale. Preserve existing changes, experiments, datasets, and checkpoints. This document is the continuing phase reference; conversation memory alone is not a durable implementation record.

Future request format: `Implement M1.02` or `Implement M2.03`. Read this roadmap, the progress ledger, repository instructions, current changes, and prerequisite evidence before working. Such a request authorizes the named phase; do not infer authorization to start training, stop a running training job, replace production artifacts, spend substantial resources, or deploy other phases. Follow any explicit session authorization for commits, pushes, or deployments. Never request or expose secret values in chat.

## Performance objective

Proposed goal: automated class-correct object precision >=90% AND object recall >=90% at the SAME frozen operating point, initially evaluated at IoU >=0.50 with one-to-one matching. Record matching rules and class scope before evaluation. Also report mAP@50, mAP@50-95, every class's support/precision/recall/AP, false alarms, confidence intervals, and performance by acquisition group. Agree class-specific and operational acceptance limits before final evaluation. Never silently exclude difficult classes to satisfy the goal.

These are targets, not guarantees. Detector mAP is not system accuracy. Human-reviewed metrics are separate from automated metrics. The historical D2 class-agnostic candidate comparison is not object-level or class-correct recall. Geographic error and runtime have separate acceptance criteria.

## Known starting evidence and defects

- Authenticated Vercel gateway production flow was verified on 1 October: HTTP 200, two Contact 105 candidates, human review, report, JSON export, one gateway call, no direct browser inference calls. This does not establish scientific correctness or future quota availability.
- Frontend audit on 2 October passed 34 tests. Preserve upload, cancellation, stale-result protection, manual retry, bounded redacted technical errors/countdown, and explicit verified examples with zero inference calls.
- Local API files in `ai/api/gate_f8_api_server.py` and the deployment copy have an indentation error at line 200 in existing uncommitted edits. Coordinate adapter imports a missing type and does not compute actual sonar/geographic coordinates.
- Public HF wrapper observed on 2 October uses conflicting class labels, dummy image/artifact hashes, fixed reliability/support and localization uncertainty, empty quality assessments, and pixel-only localization. Existing local class-map edits do not prove hosted correction.
- Canonical training order to VERIFY against actual checkpoint: 0 crab pot, 1 submarine pipeline, 2 shipwreck, 3 ghost net, 4 mine cylinder. Audit policies/calibration, not only display strings.
- V6 recorded val_clean summary: precision 74.7%, recall 69.1%, mAP50 70.4%, mAP50-95 47.8%. A V6 historical-test value of 65.6% remains unverified; do not attribute it without exact artifacts.
- Recorded D2 comparison: candidate recall 88.3% ->91.7%, precision 31.8% ->43.7%, FP 455 ->284 (37.6% reduction), with class-agnostic overlap and no one-to-one object matching.
- V8-A YAML points validation to existing test images. Preserve as test-informed exploratory work. Do not stop, resume, or edit an active run without authorization. The validation pass does not backpropagate; actual training overlap still needs audit. A test-informed checkpoint remains eligible for subsequent independent evaluation.
- Historical test measurements retain their original meaning. Subsequent selection makes that set unsuitable as untouched final evidence for subsequent models. Formally classify it as HISTORICAL_TEST/REGRESSION or DEV; do not claim both roles simultaneously for final validation.
- Existing enhancement experiments degraded detection; do not enable denoising/CLAHE by default. Tiled-only performance was worse; hybrid aggregate gains were small, despite Contact 105 recovery.
- Missing: raw logs, navigation ingestion, physical dimensions, actual geographic conversion, measured motion correction, edge evidence, durable/shared records, complete dimensional CSV, complete freeze integrity and reproducibility.
- Local `/detect` is a stub; `/report` provides metadata rather than an artifact. Public frontend uses Gradio through gateway. HF offers no shared review endpoint. Keep endpoint documentation accurate.

## Change and completion rules for every phase

1. Capture starting commit, dirty files, relevant artifact/config hashes and deployed revision where relevant. Inspect existing work before editing. Work on a dedicated branch unless the user specifies otherwise.
2. State bounded scope, prerequisites, deliverables and verification. Stop dependent work if a prerequisite is absent; continue authorized independent work. Record missing input, never substitute fake measurements.
3. Add focused tests for concrete risks. Do not use GPU inference for routine mocks. Preserve historical fixtures; version regenerated/corrected outputs separately.
4. Pass relevant tests and review the diff. No release that quietly changes class semantics, learned artifacts, thresholds, or contract without appropriate validation.
5. Update the ledger with status: PLANNED, IN_PROGRESS, IMPLEMENTED_UNVERIFIED, VERIFIED_LOCAL, VERIFIED_DEPLOYED, or WAITING_FOR_INPUT. Attach actual commands/results, artifact identities, limitations and rollback.
6. Model-dependent files remain traceable and licensed. Supply checksums and acquisition/setup instructions through an appropriate artifact channel; do not commit secrets or blindly add large/private datasets.
7. A phase requiring real survey data, target hardware, or production testing cannot be closed by mocks alone. Mark the implementation and remaining verification separately.

## Module 1: software and deterministic capabilities

### M1.01 — Baseline, preservation and issue register
Prerequisites: none. Inventory current Git changes, running processes (read-only), deployed revisions, artifacts and dependency environments. Preserve recoverable changes/checkpoints without interrupting training. Establish branch, issue register, release boundaries and rollback. Gate: source/artifact inventory and existing test baseline recorded; no existing work lost.

### M1.02 — Runnable backend and predictable startup
Requires M1.01. Repair syntax and import paths, reconcile missing coordinate types, separate model initialization from import-time schema tests, expose accurate startup/readiness failures for missing artifacts. Use a compatible pinned inference environment and documented local setup. Gate: syntax/import tests pass; actual artifact-backed service starts where artifacts are available; malformed/undecodable image errors are controlled. Do not change learned weights or pretend health proves GPU availability.

### M1.03 — Class identity and artifact compatibility
Requires M1.02. Compare checkpoint names, data labels, central map, fusion features, policy keys, unknown-profile artifacts and calibration. Eliminate conflicting active maps; serialize class-map/version with artifacts. Reject unknown/mismatched artifact identities. Until fitting repairs are validated, route affected unsupported class policies to explicit REVIEW/uncalibrated behavior. Gate: tests cover all five classes and policy lookup; same label meaning across wrappers and exports. Mapping repairs do not automatically validate historical class-specific artifacts.

### M1.04 — Shared analysis implementation and candidate merging
Requires M1.03. Create one pipeline used by local FastAPI and Gradio; reproducibly package deployment source rather than duplicate logic. Review GPU initialization/allocation, global/tile coordinate transforms and cancellation boundaries. Replace centre-only duplicate suppression with validated class/overlap handling and deterministic ordering. Gate: transport-independent semantic equivalence; adjacent contacts survive; duplicates, edges and tiled padding are tested. Keep model/settings fixed during this comparison. If `/detect` is supported, use shared real detection; otherwise explicitly deprecate the stub and test that it cannot advertise successful analysis.

### M1.05 — Honest metadata and versioned contract
Requires M1.04. Hash exact analyzed inputs and distinguish original uploads from Gradio-converted inputs. Hash actual artifacts; record pipeline revision, map, preprocessing and feature versions. Remove dummy hashes and fixed reliability/uncertainty. Compatible existing estimates may be loaded; otherwise use explicit nullable unavailable/uncalibrated states. Populate quality assessments with NOT_ASSESSED distinct from no issue. Validate finite scores, bounds, class consistency, summaries, and coordinate/status consistency server-side and in browser. Gate: every claimed measurement has a traceable source; historical fixtures remain identifiable; both adapters and frontend accept the documented contract. Learned calibration is M2.07.

### M1.06 — Complete exports and restore sessions
Requires M1.05. Add box corners/centres, pixel dimensions/area, conditional physical extents, calibration/quality/provenance, human notes and source disclosure to report/CSV. Preserve unchanged AI output in JSON. Add IndexedDB session persistence, version migration, storage limits, deletion, portable record export/import, and corrupted-record recovery. Gate: refresh restores paired image/result/reviews; records cannot mix; CSV formula protection; print/JSON/CSV labels consistent; unavailable fields explicit. Distinguish model-predicted class from human assessment.

### M1.07 — Gateway and resource hardening
Requires M1.05. Keep server-only HF_TOKEN and direct image upload/small gateway reference. Verify cache-path handling and decoded image resource limits, auth/error redaction, cancellation, stale results, controlled timeout and inference completion. Add appropriately backed concurrency/usage controls; don't claim in-memory serverless counters enforce global limits. Keep reachability separate from capacity. Document finite shared quota and public gateway abuse exposure. Gate: quota with/without countdown, invalid token, timeout, offline, malformed output, foreign references, large image and cancellation tests; offline examples zero inference calls. No automatic inference retry or silent anonymous fallback.

### M1.08 — Metadata contract and upload
Requires M1.05, representative metadata. Define timestamp/row/ping association, units, CRS, channel side, sample/range geometry, altitude, navigation/pose and offsets as supported by actual source. Add sidecar upload and validation; record source and coverage. Gate: real sample parsed; missing/stale/inconsistent metadata yields explicit capability limitations; JPG/PNG only path preserved. Synthetic tests verify implementation, not field accuracy.

### M1.09 — Geographic conversion and physical extents
Requires M1.08, real navigation and reference targets. Implement image->ping/sample->supported sonar geometry->ground-relative->geographic conversion including supported time/pose/offset effects. Estimate physical extents only with sufficient geometry. Report uncertainty components and coordinate provenance; never reuse pixel error as metres. Integrate valid points and survey context with map; default PIXEL_ONLY when insufficient. Gate: analytical/synthetic tests plus real reference-location error report at pre-agreed bounds; no fake pins; statuses match actual coordinates. Empirical learned/error calibration belongs M2.07.

### M1.10 — First raw log format and bounded survey jobs
Requires M1.08/09 and licensed representative log/specification. Choose ONE actual XTF or JSF format/version. Parse samples/channels/ping/navigation to a canonical representation; bounded windows with reversible source mapping; reconcile overlapping-window contacts. Design jobs/progress/cancel and large uploads outside Vercel's small body path, with secure upload/reference validation and retention. Gate: real log->detections->map when metadata permits->exports; source ping traceability; malformed/truncated files; bounded resource use. Second format is a separate later subphase, not a completion claim for both.

### M1.11 — Acquisition quality and deterministic motion processing
Requires M1.10 and pose-bearing data. Flag gaps/dropout/saturation/navigation unreliability. Validate nadir/channel interpretation. Correct supported geometry using timestamped pose; do not invent missing acoustic data or claim image-only motion recovery. Gate: supported real conditions and reference transforms; warnings/exclusions visible; original-to-corrected mapping retained. Learning robustness against residual artifacts belongs M2.04/05.

### M1.12 — Shared review and durable records
Requires M1.06/07 and user-selected hosting/storage. Add authenticated analyses/reviews, reviewer identity, revisions, permissions, quotas and retention; keep AI immutable and human conclusions separate. Backend report artifacts only if an actual artifact service is introduced. Gate: isolation/access tests, concurrent edits, durable restoration, record export/deletion. Browser-local persistence can ship before this; no free-service capacity guarantee.

### M1.13 — Offline packaging and existing-model hardware benchmark
Requires M1.04/05 and target device. Package local analysis using known artifacts. Compare a compatible exported runtime with native output; measure full pipeline memory, p50/p95 latency, throughput and power where feasible. Test global/selective/full tiled cost and disconnected operation. Gate: new inputs processed offline on actual device within agreed resource budget, conversion differences measured. Dataset-calibrated quantization/distillation is M2.09. Oracle 1 GB VM is not assumed viable.

### M1.14 — Integrated software release and compliance report
Requires relevant completed M1 phases; missing data-dependent capabilities must remain explicitly open. Verify live/viewer/review/report/export, examples, refresh, metadata/log paths, safety of invalid inputs, secret leakage and cancellation. Record complete artifact manifest, source/deployment match, setup and rollback. Reconcile F9 reference discrepancy without overwriting history; new release must not claim intact historical freeze. Gate: deployed smoke where authorized; truthful PS matrix; no fake capability/performance claims. Rerun after promoted M2 artifacts.

## Module 2: data, training and performance evidence

### M2.01 — Dataset and selection-history audit
Requires M1.01; can run while backend repair proceeds. Inventory licenses/labels/source recordings/sites/missions; SHA256 and similarity review; crop parent lineage; exact/near-duplicate and group leakage. Record ever-used roles as YES/NO/UNKNOWN with evidence. Classify TRAIN, DEV, CALIB, HISTORICAL_TEST/REGRESSION, FINAL_TEST_CANDIDATE. Do not infer independence from missing records or printed preflight text. Gate: reproducible split manifest and explicit unresolved provenance. No new training yet.

### M2.02 — Freeze evaluation definitions and protected splits
Requires M2.01 and verified class semantics M1.03. Define one-to-one class-correct matching, IoU, duplicate treatment, all class denominators and no-detection behavior. Predefine primary 90/90 operating-point objective, class limits, false alarms, CI method accounting for acquisition grouping and stress strata. Establish actual DEV/CALIB; reserve independent external/group-disjoint final set with enough class/site support. Add automated guards against protected data in training/mining/calibration. Gate: evaluator checked on known outcomes; manifests and methodology signed off. Avoid claiming complete non-overlap with unknown pretraining provenance.

### M2.03 — Comparable existing-checkpoint baseline
Requires M2.02 and M1.04. Compare V6, available V7 and V8-A exploratory checkpoints on DEV using same evaluator/settings. Record PR curves, confusion, per-class/size/site errors, candidate-generation ceiling, backgrounds and full pipeline with explicitly compatible artifacts. Unavailable fusion/calibration cannot be borrowed to pretend a complete comparison. Verify source of every historical metric. Gate: repeatable leaderboard and failure taxonomy. No automatic model promotion; V8 is not better because newer.

### M2.04 — Targeted data and robustness corpus
Requires M2.03. Gather real hard positives (especially weak crab/shipwreck classes), diverse nets/pipes/cylinders, confusing natural negatives and sensor/site variation. Review boxes/class labels; preserve full-scene/context and parent grouping. Build DEV stress conditions for speckle/gain/resolution/shadows/dropout/motion alongside real conditions. Mine only permitted development/training pools; never final set. Gate: licensed, audited dataset revision addressing documented errors, frozen manifests, representative independent diversity. Augmentation alone is not external evidence.

### M2.05 — Controlled detector experiments
Requires M2.04. Run separately bounded subphases: targeted-data fine-tuning; small-object resolution/P2/tiling; sampling/balance; sonar augmentations; architecture change only if justified. Prefer compatible known baseline. One major factor per comparison; record seeds, training settings/checkpoints, DEV results, resource cost and regressions. Verify effective YAML before launch; startup guards prevent final-test validation. Do not change active run inputs. Gate: reproducible DEV benefit and acceptable critical-class/runtime tradeoffs. Stop unproductive branches; no fixed epoch count or training duration guarantees 90%.

### M2.06 — Refit fusion and decision artifacts
Requires selected M2.05 detector or M2.03 baseline, M1.05. Regenerate evidence and class-correct outcomes on appropriate training/development groups. Use out-of-sample candidate generation or document bias when training a downstream scorer; prevent scaler/feature fitting on protected data. Compare detector-only and fusion at matched recall; audit known-profile anomaly model; version features/map/policy. Freeze supported review/confirm scope. Gate: measured DEV benefit without hiding missing detector candidates. Learned thresholds/calibration finalized in M2.07.

### M2.07 — Calibration and operating point
Requires M2.06, isolated CALIB, corrected contract. Fit compatible score calibration and select thresholds per predeclared method; honest support/intervals; insufficient classes uncalibrated. Assess heuristic 1-fusion uncertainty rather than calling it calibrated. Fit/validate localization error envelopes only with actual reference data. Freeze detector, preprocessing, tiling, merge, fusion, anomaly model, calibration, thresholds and policies. Gate: traceable calibration artifacts and locked complete pipeline. Repeated redesign informed by CALIB requires documenting/adapting the calibration protocol; CALIB is not final evidence.

### M2.08 — Independent external evaluation
Requires M2.07 and untouched final set. Evaluate frozen pipeline; report precision AND recall at same point, mAP50/50-95, per-class support/AP/CI, false alarms and strata. Compare fixed baseline on same data without using results to choose an undisclosed winner. Measure localization/runtime separately. Gate: 90/90 claim only if actually achieved for declared scope; report intervals and weak conditions. A failed target is a measured result, not permission to redefine accuracy. Subsequent tuning informed by findings requires a new independent final gate. QA access/repeated deterministic execution is not inherently leakage; adaptive selection is the concern.

### M2.09 — Edge optimization with data-based fitting
Requires M1.13 and selected model. Quantization calibration uses permitted data, not final set. Assess distillation/compact retraining only as needed. Verify optimized candidate's class/score semantics, accuracy and full resource budget; recalibrate changed scores. Gate: native/optimized comparisons and device evidence; optimized model is a separate release candidate. If optimization is planned, run this phase BEFORE the final M2.08 gate or reserve separate final evidence afterward.

### M2.10 — Model promotion and final release
Requires M2.08 and relevant M1 capabilities. Promote compatible detector/fusion/policy/calibration as one identified bundle, generate new traceable examples separate from historical F9, rerun M1.14 regression and authorized production live check. Update measured results, license/artifact instructions, diagrams and PS matrix. Gate: deployed artifact hashes match verified artifacts; rollback and actual capabilities documented. If data/hardware-dependent requirements remain open, do not call all PS gaps solved.

## Recommended global execution order

1. M1.01 baseline; M2.01 provenance may proceed alongside M1.02 repairs.
2. M1.02 -> M1.03 -> M1.04 -> M1.05; M2.02 -> M2.03 once their prerequisites pass.
3. M1.06 and M1.07; publish a corrected image-workflow release if verified and authorized. Do not wait for unavailable raw survey data to repair misleading output.
4. M1.08 -> M1.09 -> M1.10 -> M1.11 as real data permits. M1.12 after storage selection. These inform realistic requirements, not model training prerequisites for every image-only experiment.
5. M2.04 -> individual M2.05 experiments -> M2.06 -> M2.07. M1.13 hardware benchmarking can begin with existing verified model.
6. If optimizing, M2.09 -> refresh affected M2.07 artifacts -> M2.08 final evaluation. Otherwise M2.07 -> M2.08.
7. M1.14 integrated verification -> M2.10 promotion. Re-run required release verification on deployed bundle. Never skip prerequisite gates solely to fit a presentation deadline.

## Required external inputs and decisions

- Actual deployed weights/fusion/policies/calibration and their training identities.
- Licensed dataset/annotation manifests, selection history and independent test sources.
- Real sonar logs and supported format documentation; aligned navigation/pose/acoustic geometry.
- Known target reference positions/extents and field-error acceptance limits.
- Target hardware, power/memory limits, required acquisition throughput and latency.
- Hosting/storage and authentication choice for durable multi-user records and large jobs.
- Per-class performance and false-alarm tolerances; enough samples to support statistical claims.

Do useful independent phases while these inputs are pending. Never invent measurements, approvals, navigation, labels, or guarantees.

## Progress ledger

Initial Module 1 implementation is recorded in [MODULE1_IMPLEMENTATION.md](MODULE1_IMPLEMENTATION.md). Read that phase ledger before future implementation; unverified/data-dependent phases remain open. Module 2 has not started.

| Phase | Status | Starting/ending revision | Verification and evidence | Remaining input / rollback |
|---|---|---|---|---|
| M1.01-M1.14 | MIXED; see detailed ledger | codex/module1-hardening | MODULE1_IMPLEMENTATION.md | Real survey, durable hosting, target hardware, production verification |
| M2.01-M2.10 | PLANNED | Not started | See phase-specific gates | See prerequisites |

Each handoff must state: completed phase, changed files, exact tests/results, artifact IDs, deployed vs local status, remaining risks, and next eligible phase. A request to implement a later phase must first check prerequisites rather than silently running the whole roadmap.


## Real survey update — 3 October 2026

M2.01/M2.02 have partial non-training implementation for the new survey: identity/provenance audit, protected role/group/hash/label preflight and a human annotation queue. This does not close the broader existing-data audit or final evaluator/split protocol. See [USGS_SURVEY_READINESS.md](USGS_SURVEY_READINESS.md). M2.03-M2.10 remain pending; no training was started.
