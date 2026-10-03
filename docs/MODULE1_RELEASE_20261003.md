# Module 1 release and remaining verification

Updated 3 October 2026. This document supersedes older deployment and raw-workflow status in the initial Module 1 report. No training, weight promotion, threshold fitting or calibration fitting occurred.

## Completed software and evidence

| Area | Completed and tested | Scope |
| --- | --- | --- |
| Backend/contracts | Correct model identity, common analysis runtime, provenance, explicit unavailable calibration, REVIEW decisions | Frozen artifacts unchanged |
| Records UI | Cloud fields, action groups, review-history entries and portable-record toolbar match workspace spacing; desktop and mobile layout checked | Local release browser |
| Records/reports | Paired-image hash validation, local refresh restore, cloud save/open, immutable review revisions, JSON/CSV/print and complete-record transfers | Browser cloud walkthrough mocked; user confirms hosted sign-in/open and identical review note after refresh/restore |
| Usage controls | Production fails closed without durable admission; concurrency, finite daily budget, expiry/release and service-only RPC checks; protected daily maintenance | Embedded PostgreSQL checks passed; hosted SQL probe/actual scheduled cleanup need confirmation |
| Real XTF input | All 143 logs decoded for supported sonar packets: 2,068,844 channel rows and 8,473,985,024 samples; no failed files, invalid timestamps or nonfinite metadata | Vendor-specific packets are not interpreted; decoding is not field validation |
| Raw workflow | Bounded raw-log â†’ PNG â†’ local analysis â†’ interactive offline viewer â†’ human review â†’ CSV/JSON/GeoJSON; resumable hashed outputs; grid-aware overlap reconciliation | Four real windows processed with zero candidates; no geographic values invented |
| Geometry/quality | Explicit source-bound operator profile; per-ping WGS84 heading projection, pose-rotated lever arm, flat-bottom slant correction, estimated raster dimensions; quality/gap/saturation warnings | Synthetic mathematical tests; real orientation/pose/altitude/datum alignment and known contacts not independently verified |
| Offline/exports | Private native bundle, unchanged-checkpoint ONNX export and raw-tensor comparison | Not a full ONNX pipeline-equivalence or target-edge certification |
| Release | 46 frontend tests, 34 backend tests, lint/typecheck/build/secret-pattern scan, SQL regression, browser viewer/review/report and four examples | Current task consumes zero HF inference runs |

## Run the actual raw workflow

Use an isolated inference environment with `requirements-inference.txt` and `requirements-raw.txt`; do not replace a running training environment.

```powershell
Set-Location "E:\GITHUB\a sih 2026"
python -B scripts/analyze_xtf.py datasets/xtf/15CCT03_SSS_150528172600.xtf --device cpu --rows 128 --overlap 16 --max-windows 4 --output-dir .temp/my-survey
Start-Process .temp/my-survey/index.html
```

Open a window, select any detected candidate, inspect evidence, save a human note, then export analysis and human reviews. Survey CSV/JSON contains original machine observations; viewer review export contains the separate human assessments. Zero-candidate windows are valid outputs and do not demonstrate debris absence across the entire survey.

Add `--resume` with identical parameters to continue or reopen a bounded job. Source, code, geometry and output hashes must agree; tampering or changed settings fail safely. Opening HTML reports or resuming already completed windows makes no additional model inference calls. Local raw inference does not use the HF GPU quota. Raw processing is local, not a Vercel multi-gigabyte upload service.

## Geographic results and acquisition corrections

`--geometry-profile reviewed-profile.json` activates `SurveyGeometry` in `ai/runtime/sonar_geometry.py`. It requires an exact source-log SHA256; explicit authorization, WGS84/nav-unit/timezone assertions; sensor versus vessel navigation; per-channel side/sample order; traceable altitude/heading/pose references; metre scale and verified zero heave. Vessel offsets must be measured in metres. No configuration is guessed from a diagram or filename. Sensor navigation must not receive vessel lever arms twice.

Supported corrections are flat-bottom slant-to-ground resampling, per-ping heading, and pose rotation of the GPS-to-sensor lever arm. Full beam pitch/roll footprint compensation, unaligned heave, sloping-bottom and missing-sample reconstruction remain unsupported. Unsupported attitude/heave, navigation gaps/jumps and source disagreements are rejected. Dimensions are estimated raster extents, not measured object dimensions. Geographic output is marked OPERATOR_CONFIGURED_NOT_FIELD_VALIDATED. Confidence calibration and position uncertainty remain unavailable.

For independent field verification, provide matched known target positions and measurements, not merely vessel track points. CSV columns: `candidate_id,latitude,longitude,reference_source,reference_uncertainty_m,width_m,height_m` (last two optional).

```powershell
python -B scripts/validate_survey_positions.py .temp/my-survey/report.json independently-measured-targets.csv --output .temp/field-errors.json
```

The script reports matched-location/dimension error and explicit reference coverage. It does not manufacture detector precision/recall or validate unobserved contacts. The downloaded geological survey does not supply confirmed hazard labels or target measurements; 90% detection or field accuracy cannot be claimed from it.

## Actual available hardware results

Windows i7-13620H workstation, approximately 16 GiB RAM, Contact 105, native CPU tiled full pipeline: cold 7.437 s; ten warm runs median 1.5645 s, observed nearest-rank p95 1.9151 s; sampled peak RSS approximately 742 MiB. This is one input on the available computer, not Raspberry Pi/Jetson or marine-drone certification; power was not measured.

Private 640px ONNX export produced matching raw output shape `[1,9,34000]`, maximum absolute error 0.00076294, within the configured comparison tolerances. Raw inference medians were 0.20966 s PyTorch versus 0.25755 s ONNX on this CPU; no speed improvement is claimed. Postprocessing/evidence/fusion equivalence and accuracy are not established by tensor comparison.

## Finish the hosted checks now

1. Load a verified example, Save to cloud, add a distinctive human note, Sync reviews to cloud, refresh, sign in, Load cloud records and Open. Confirm image and note both return. Reports â†’ JSON/CSV/Print uses the loaded cloud record; there is no separate cloud PDF.
2. Run `supabase/verification/module1_usage_probe.sql` in Supabase SQL Editor while no analysis is running. Confirm all five rows show `passed = true`. The probe restores its temporary changes automatically and consumes no inference quota.
3. In the Vercel deployment's cron controls, run `/api/maintenance` and inspect its invocation result. It must authenticate with server-only CRON_SECRET; verify a successful scheduled invocation and that expired storage is deleted before its database rows. An anonymous 401 confirms protection, not successful cleanup. Server secrets must remain out of chat and public variables.
4. Deploy the tested revision and verify the new toolbar plus a saved-example viewer â†’ review â†’ report walkthrough. GPU inference availability remains separate from Space reachability.

## Honest closure boundary

Software can be completed and local release verified with available inputs. Full Module 1 certification still requires independently measured survey targets and verified sensor geometry, confirmation of the hosted usage/maintenance checks, and actual target hardware if edge certification is required. No separate edge device is available. These are evidence prerequisites, not substitutes for tests or permission to invent measurements. Module 2 remains responsible for verified calibration, labeled validation and any training; no automatic 90% precision/recall guarantee is made.

Evidence is saved under `docs/metrics/module1-*-20261003.json`. Private weights, ONNX exports, raw logs and reviewer credentials are excluded from Git.
