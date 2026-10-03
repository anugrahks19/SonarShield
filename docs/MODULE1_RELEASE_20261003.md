# Module 1 release and remaining verification

Updated 3 October 2026. This document supersedes older deployment and raw-workflow status in the initial Module 1 report. No training, weight promotion, threshold fitting or calibration fitting occurred.

## Completed software and evidence

| Area | Completed and tested | Scope |
| --- | --- | --- |
| Backend/contracts | Correct model identity, common analysis runtime, provenance, explicit unavailable calibration, REVIEW decisions | Frozen artifacts unchanged |
| Records UI | Cloud fields, action groups, review-history entries and portable-record toolbar match workspace spacing; desktop and mobile layout checked | Local release browser |
| Records/reports | Paired-image hash validation, local refresh restore, cloud save/open, immutable review revisions, JSON/CSV/print and complete-record transfers | Browser cloud walkthrough mocked; user confirms hosted sign-in/open and identical review note after refresh/restore |
| Usage controls | Production fails closed without durable admission; concurrency, finite daily budget, expiry/release and service-only RPC checks; protected daily maintenance | Embedded PostgreSQL checks passed; all five hosted checks passed in user screenshot; two user-reported maintenance HTTP 200 invocations; automatic scheduling and actual expired-image deletion not observed |
| Real XTF input | All 143 logs decoded for supported sonar packets: 2,068,844 channel rows and 8,473,985,024 samples; no failed files, invalid timestamps or nonfinite metadata | Vendor-specific packets are not interpreted; decoding is not field validation |
| Raw workflow | Bounded raw-log â†’ PNG â†’ local analysis â†’ interactive offline viewer â†’ human review â†’ CSV/JSON/GeoJSON; resumable hashed outputs; grid-aware overlap reconciliation | Four real windows processed with zero candidates; no geographic values invented |
| Geometry/quality | Explicit source-bound operator profile; per-ping WGS84 heading projection, pose-rotated lever arm, flat-bottom slant correction, estimated raster dimensions; quality/gap/saturation warnings | Synthetic mathematical tests; real orientation/pose/altitude/datum alignment and known contacts not independently verified |
| Offline/exports | Private native bundle, unchanged-checkpoint ONNX export and raw-tensor comparison | Not a full ONNX pipeline-equivalence or target-edge certification |
| Release | 47 frontend tests, 43 backend tests, lint/typecheck/build/secret-pattern scan, SQL regression, browser viewer/review/report and four examples | Current task consumes zero HF inference runs |

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

Software can be completed and local release verified with available inputs. Full Module 1 certification still requires independently measured survey targets and verified sensor geometry, observed automatic maintenance scheduling/expired-image deletion, and actual target hardware if edge certification is required. No separate edge device is available. These are evidence prerequisites, not substitutes for tests or permission to invent measurements. Module 2 remains responsible for verified calibration, labeled validation and any training; no automatic 90% precision/recall guarantee is made.

Evidence is saved under `docs/metrics/module1-*-20261003.json`. Private weights, ONNX exports, raw logs and reviewer credentials are excluded from Git.


## Latest closure work: browser raw uploads and production checks

The user's Supabase screenshot confirms all five usage-control checks passed. The user also supplied two successful HTTP 200 `/api/maintenance` logs at 11:00:30.82 and 11:00:54.95 IST on 3 October 2026. These establish authenticated maintenance invocation, not observed deletion of an actual expired image or automatic execution at the daily scheduled time. Existing cleanup tests prove failed Storage deletion does not prune the database record.

A loopback-only raw dashboard now accepts streamed XTF uploads up to 2 GiB, rejects uploads when existing stored data plus the new input exceeds the 4 GiB admission budget (generated output can add to that budget), permits one active CPU job and at most 100 windows per job, and offers explicit cancellation/resume. Host/origin/session checks reject cross-site requests; only generated result filenames can be read. Dashboard restarts restore job listings without starting inference. Keep this local; it is not an internet-hosted raw-data service. Jobs interrupted during inference can resume only after their previous process is confirmed stopped; stale job locks are not removed automatically.

Setup reuses the existing inference packages through a separate virtual environment; it does not modify the active training environment:

```powershell
Set-Location "E:\GITHUB\a sih 2026"
python -m venv --system-site-packages .venv-survey
.\.venv-survey\Scripts\python.exe -m pip install -r requirements-raw.txt
.\.venv-survey\Scripts\python.exe scripts/start_survey_dashboard.py --output-dir .temp/survey-dashboard --port 8766
```

Open `http://127.0.0.1:8766/`. Choose an XTF file, optionally attach a reviewed geometry profile, select bounded window settings and click **Upload and run local CPU analysis**. Then **Open viewer and reports**. Results remain explicitly local inference; this does not change the Vercel live-first/verified-example paths. A fresh system also needs the packages in `requirements-inference.txt` and the licensed frozen artifacts; missing dependencies fail explicitly.

Real browser verification used `15CCT03_SSS_153_150602205800.xtf` (5,228,224 bytes, larger than Vercel's gateway body limit), one real CPU window, verified source hash, local reports/export, desktop/mobile layouts and zero external requests/HF calls. A separate synthetic geometry fixture verified selecting geographic markers, saving/restoring reviews and exporting; it is not a measured field-accuracy result. The raw viewer's geographic display is a local WGS84 extent plot without an online basemap.

Reports now include original pixel box corners/dimensions, detector score percentages and acquisition flags. Zero rows are retained and disclosed, with candidate-level dropout-intersection warnings. Pitch/roll departures and unresolved heave trigger review warnings. A single ping cannot establish along-track dimensions, so its height is explicitly unavailable. No pixels or motion measurements are fabricated to hide data loss.

Remaining scientific capabilities are full beam/terrain/heave correction using verified synchronized inputs and independent field accuracy. These stay partial in the PS compliance matrix; missing samples cannot be recovered from absent measurements. Calibration belongs to Module 2. Target edge hardware and power are unavailable; the actual Windows benchmark remains the only hardware certification scope.


## XTF rendering defect repaired after user visual report

The prior full-scale UINT16 rendering lost usable sonar contrast: the actual user log had median amplitudes 25-27 on a 65,535 storage scale, producing median PNG value zero. The prior "browser passed" gate checked navigation and export, and did not adequately validate image visibility or result-page styling. It must not be interpreted as validation of the original rendering's usability.

Default raw conversion now uses deterministic log1p amplitude mapping with 1st/99.5th percentile endpoints, preserving zero/dropout samples and recording all transform parameters per window. It is not a learned enhancement and not a validated detector preprocessing domain. Existing model weights/thresholds remain unchanged. Independent raw-log labels are needed to assess detection accuracy under this conversion.

The exact 55,071,424-byte user log was rerun on local CPU as a new job with four windows, producing 1/3/1/0 REVIEW candidates. This establishes functioning image input and candidate/report flow, not correct hazard identification. Browser verification checked real candidate selection, review refresh/export, readable controls and sidebar layout; no HF inference calls occurred.

Existing jobs keep their original PNG and analysis JSON hashes. Their repaired viewers may use source-derived contrast previews clearly labelled as display-only; old results are not relabelled as corrected inference. The new corrected job uses its actual analyzed PNG. Do not resume a job across changed rendering/source identity; create a new job.

Index and window pages now share dark workspace styling, UTF-8 labels, proper input/buttons, a readable candidate summary and collapsed technical evidence. Empty geographic plots are hidden; review controls are disabled until selecting an actual candidate. Default inspection display expands ping rows and labels the independent axis scaling; native pixel aspect remains available. Physical dimensions must never be inferred from stretched display pixels.

Relevant evidence: `module1-xtf-visual-fix-20261003.json`, `module1-corrected-xtf-run-20261003.json`, `module1-corrected-xtf-browser-20261003.json`. Three additional amplitude-rendering regressions bring backend/preflight tests to 43. Full motion/field accuracy and target-edge certification remain open as stated above.
