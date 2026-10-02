# Module 1 implementation and remaining verification

Date: 2 October 2026. Checkout: `E:\GITHUB\a sih 2026`. Branch: `codex/module1-hardening`.
This is a local implementation report, not a production deployment or a 90% accuracy claim.

## Preserved baseline
Existing tracked changes and nonignored untracked files were copied to `.temp/module1-baseline-20261002/`, with status, binary diff and starting revision. Original datasets, training scripts, running processes and learned artifact files were not overwritten. Large ignored artifacts remain in their original locations; inventory hashes are in `metrics/module1_artifact_inventory.json`. The prior production inference gateway remains deployed until a coordinated release is authorized.

## Phase ledger

| Phase | Status | Evidence / remaining work |
|---|---|---|
| M1.01 | VERIFIED_LOCAL | Backup, dedicated branch, source and artifact inventory. Remote deployment revision comparison still needed for new release. |
| M1.02 | VERIFIED_LOCAL | Lazy safe imports, controlled missing-artifact/input errors, actual CPU inference. |
| M1.03 | VERIFIED_LOCAL for checkpoint identity | Actual V6 checkpoint names match canonical map. Existing class-specific policy/calibration identities remain unverified; corrected runtime forces REVIEW rather than applying wrong-ID policies. |
| M1.04 | VERIFIED_LOCAL for image pipeline | Shared Gradio/FastAPI pipeline and reproducible packaging; class-aware overlap/containment merge; adjacent-contact tests. No aggregate accuracy claim for changed merge. |
| M1.05 | VERIFIED_LOCAL for corrected runtime | F8.1/F7.1 output, real image and detector/fusion hashes, nullable calibration/uncertainty; historical fixtures preserved. Calibration fitting deferred to Module 2. |
| M1.06 | VERIFIED_LOCAL for browser records | Dimensional CSV/review notes, IndexedDB active-session restore/delete, portable image/result/review record import/export; browser roundtrip passed with zero inference. Authenticated service UI now supports explicit save/open/review sync; production hosting remains unactivated. |
| M1.07 | PARTIAL_VERIFIED_LOCAL | Size/pixel/metadata limits, stale decode fix, original auth/error/cancel tests, local runtime admission. Durable SQLite admission controller enforces global UTC-day budgets and concurrency leases across gateway instances when activated. Fail-closed controller tests pass. Production activation and VM/proxy checks remain pending; an unconfigured gateway retains legacy exposure. |
| M1.08 | IMPLEMENTED, FIELD_DATA_PENDING | Optional ground-range raster JSON sidecar through local API and new Gradio/gateway input. Identity/coverage/units contract and synthetic tests. Real metadata required. |
| M1.09 | IMPLEMENTED_FOR_LIMITED_GEOMETRY, FIELD_DATA_PENDING | Sensor WGS84 ground-range raster local-tangent conversion and estimated extents, bounded latitude/range. Not a general slant-range/nav solution or measured geolocation accuracy. |
| M1.10 | PARTIAL_VERIFIED_LOCAL | Optional XTF revision-42-structure adapter, packet/size caps, unsigned 8/16-bit channels, bounded local CLI, source ping lineage; synthetic binary framing tests. Real vendor logs, channel orientation, rendering and source geometry validation remain pending. Local durable job progress/resume/cancel and overlapping-window same-grid contact reconciliation are now implemented/tested. Remote large-file job hosting is still unactivated. JSF unsupported. |
| M1.11 | WAITING_FOR_INPUT | Deterministic zero-row, full-scale saturation, ping-gap and sequence warnings now propagate through survey results/reports. Thresholds are explicitly heuristic. Raw pose fields are retained but unverified. No validated heave/pitch/roll correction or reconstructed missing observations is claimed. |
| M1.12 | PARTIAL_VERIFIED_LOCAL | Opt-in SQLite API: separate reviewer credentials, ownership, immutable AI record, revision history/conflicts, deletion, quotas; tests pass. Paired image storage, runtime credential UI, explicit review sync/history, team scopes, 30-day retention and consistent backup tooling now pass local tests. Oracle setup is prepared; actual VM deployment/restore drill remains pending. |
| M1.13 | PARTIAL_VERIFIED_LOCAL | Offline CPU CLI executed actual detector/evidence/fusion; Private checksum-manifest native bundle built; actual cold + three warm CPU runs measured latency and sampled RSS. This is one workstation/input, not target-edge certification. Export-equivalence, actual edge hardware and power remain pending. |
| M1.14 | LOCAL_REGRESSION_VERIFIED, PRODUCTION_PENDING | Backend/frontend/browser gates recorded below; updated source has not been pushed or deployed to HF/Vercel. Field and hardware gaps remain open. |

## Corrected image behavior

The V6 checkpoint names are 0 crab_pot, 1 submarine_pipeline, 2 shipwreck, 3 ghost_net, 4 mine_cylinder. The saved score policy has keys 0/1/2 without a verified matching class identity. Corrected analysis therefore returns the detector label and computed fusion score, with REVIEW and POLICY_COMPATIBILITY_UNVERIFIED. Reliability is null; uncertainty is NOT_ESTIMABLE. This is a deliberate disclosed limitation until compatible policy/calibration is validated in Module 2. No weights or thresholds were fitted/rewritten.

SHA256 identifies the file actually analyzed. Gradio now uses `gr.File` rather than `gr.Image` to preserve uploaded file bytes; the named endpoint remains `/analyze_image_gradio`. Historical F9 examples retain original responses/decisions and real pair hashes. Old live F8.0 output receives a legacy scientific-metadata warning; it is not relabeled as F8.1.

`/detect` returns explicit 410 instead of a fake empty successful result. `/report` returns explicit 501 rather than inventing a nonexistent downloadable artifact. Browser JSON/CSV/print remain available. `/health` reports uninitialized vs actual runtime state and does not promise GPU capacity.

## Local setup

Use the existing verified Python environment for initial checks. It has Python 3.12, torch 2.4.1+cu121, Ultralytics 8.4.163, numpy 1.26.4, scikit-learn 1.4.1.post1, Pydantic 2.13.3, FastAPI 0.118.0, joblib 1.4.2, Pillow 11.3.0 and OpenCV 4.8.1.78. Local and HF GPU dependencies must be verified in their separate environments; do not overwrite a running training environment to install inference dependencies.

From repository root:

```powershell
python -m uvicorn ai.api.gate_f8_api_server:app --host 127.0.0.1 --port 8000
python -B scripts/offline_analyze.py frontend/public/contact-105.jpg --device cpu --output .temp/local-analysis.json
python -B -m unittest discover -s tests -p "test_module1_*.py" -v
```

Default local inference uses CPU; set SONAR_DEVICE deliberately for other hardware. A fresh clone still needs licensed detector/fusion artifacts; their absence produces a controlled error. No model is downloaded silently.

Frontend: `cd frontend`, `npm run build:release`, then `.\node_modules\.bin\vite.cmd preview --host 127.0.0.1 --port 4182`. Existing gateway-development setup remains in `frontend/docs/HUGGING_FACE_INTEGRATION.md`. The corrected HF wrapper must be deployed before using its optional metadata parameter on the public Space. Local API accepts multipart `metadata_json`.

## Supported metadata boundary

`ai/runtime/localization.py` defines `ground-range-raster-v1`. It requires an already ground-range-corrected image, its actual SHA256/dimensions, sensor (not uncorrected vessel GPS) WGS84 navigation, timezone timestamps, full row-boundary coverage, headings, nadir location and explicit across/along metre scales. Navigation gaps over 10 seconds, dateline crossings, polar latitude over 80 degrees and offsets over 1 km are rejected where applicable. It uses a short-range tangent approximation; physical dimensions are estimated raster extents, not exact measured object sizes. Real geometry/field-error validation is pending. Arbitrary raw images cannot become georeferenced by inventing a sidecar.

## Raw logs

Install optional `requirements-raw.txt` in an isolated inference environment (not the active training environment). Current tests used pyxtf 1.4.2 installed only under `.temp/module1-pyxtf`.

```powershell
python -B scripts/analyze_xtf.py path/to/survey.xtf --output-dir .temp/survey-run --device cpu --max-windows 10
```

It reads bounded packets without loading pyxtf pickle indices, caps local logs at 2 GiB and packets at 8 MiB, supports up to six channels and 4096 samples, and emits at most the requested number of windows. Outputs include PNGs, JSON analyses, source-log hash, packet offsets and ping references. Rendering is full-scale linear and UNVALIDATED for this detector. Navigation remains UNVERIFIED_UNITS_DATUM_POSE; pixel-only output is intentional. This is not a Vercel raw-log upload/job service or validated motion/geographic processor.

### Real data to download next

USGS Grand Bay 2015 release: https://coastal.er.usgs.gov/data-release/doi-P9374DKQ/ (DOI 10.5066/P9374DKQ).
- Raw XTF archive: https://coastal.er.usgs.gov/data-release/doi-P9374DKQ/data/2015-315-FA_xtf.zip — page lists **9.84 GB**. Not downloaded by this task. Extract one manageable .xtf file first; inspect individual size.
- Configuration/logs: https://coastal.er.usgs.gov/data-release/doi-P9374DKQ/data/2015-315-FA_logs.zip — page lists **80 KB**.
- Mosaic: https://coastal.er.usgs.gov/data-release/doi-P9374DKQ/data/2015-315-FA_SSSMosaic.zip — inspect size before downloading.

These are geological-survey data for parser/geometry investigation, not established debris bounding-box ground truth or reference hazard locations. Need survey documentation to establish navigation datum/units, channel orientation, corrections and sensor offsets. Additional annotated detection and known-position data are still needed for Module 2 and field localization.

## Optional shared records

Disabled unless SONAR_RECORDS_DB points to durable local SQLite storage and SONAR_REVIEW_TOKENS_JSON supplies a server-only mapping of reviewer IDs to independently generated tokens of >=32 characters. Never use HF_TOKEN as a reviewer credential. Send reviewer credentials at runtime as Bearer authorization over HTTPS; do not bundle them in VITE variables. Provision them privately outside chat/source. No real tokens were created in this task.

`/records` POST validates and stores client-imported analysis/source without claiming server attestation. `/records/{id}` GET returns owned analysis and review history; POST `/records/{id}/reviews` uses previous_revision for optimistic concurrency; DELETE removes the owned record/history. AI payloads are immutable; reviewer identity comes from credentials, not the request body. Requests authenticate before bounded JSON parsing. Maximum 100 records per owner, 2 MiB stored analysis, bounded notes. Operational backup, expiry/retention, per-team sharing, browser login/sync and chosen hosting remain open. SQLite on ephemeral HF/Vercel storage is not durable cloud persistence.

## Verification and release

Focused backend tests cover safe imports, invalid/missing artifacts, class identities, adjacent/contained boxes, unavailable calibration, busy admission, metadata identity/gaps, optional binary XTF framing (including ignored unsafe index), bounded windows, record auth/isolation/immutable payload/conflicts/deletion. Frontend tests retain all ten frozen F9 fixtures and auth/error/export guards. Browser checks include all offline examples, nine mocked success/error cases (including actual corrected CPU-output rendering), refresh and portable record roundtrip without inference.

Initial-pass local gates: **38 frontend unit tests**, ESLint, TypeScript and production build passed; **12 backend tests** passed with isolated pyxtf available. Nine mocked gateway scenarios passed with no browser errors and no live Space inference. The actual tiled CPU smoke run returned two REVIEW candidates in 11.238 seconds cold on this workstation; this is one sample, not a benchmark of accuracy or edge performance. Browser record refresh/import/export and all four offline example walkthroughs passed without inference.

Remaining verification: real raw survey parsing/rendering/geometry, known-target geographic error, full acquisition motion model, hosted job storage/security, edge memory/power/throughput, new HF SDK/dependency behavior and production F8.1 viewer-to-report flow. No 90% claim or intact F9 freeze certification.

Deployment order when authorized: package canonical sources with `python scripts/package_space.py`; stage HF artifacts/source and test F8.1 contract/actual hashes/REVIEW-only behavior; stage frontend/gateway against that backend; verify one real request and all source labels/exports; then promote. Do not promote production until coordinated checks pass. Roll back compatible backend/frontend versions together. Preserve .temp baseline and previous deployed revisions until release is accepted.


## Second implementation pass: work independent of survey download

The 1 GB Oracle VM is an appropriate candidate for the lightweight records/admission service, subject to actual available resources and deployment checks. It never imports torch, Ultralytics or OpenCV and does not host inference. See [ORACLE_CONTROL_SETUP.md](ORACLE_CONTROL_SETUP.md) for architecture, exact private/server/public configuration boundaries, systemd/reverse-proxy examples, quotas, backup/restore and rollback. The VM was not accessed. HF remains the sole hosted live inference service.

New software includes:

- Persistent global gateway admission with conservative expiring leases and UTC daily budgets; no in-memory serverless counter claim. Both secrets must be configured for production activation; controller failures reject before HF inference. Public visitors can still exhaust the finite admitted budget; these controls do not make inference unlimited or eliminate denial of service.
- Shared paired-image records, explicit account/team permissions, original AI preservation, optimistic review revisions, bounded total storage, expiry pruning and consistent SQLite backup. Optional browser connection credentials remain memory-only. The actual local service + browser restoration/report flow passed with no inference or browser errors.
- Deterministic acquisition flags and local bounded survey jobs with atomic progress, source/config/artifact identity checks for resume, cancellation between windows, and comparable same-channel/sample-segment overlap reconciliation. No real raw-log rendering, motion correction or geographic validation is claimed.
- Known-credential/HF-pattern scanning of built assets; public credential-name guard also checks Vite env files. Legacy scientific-metadata warnings now reach print and JSON/CSV. No scanner can guarantee absence of all unknown secrets.
- Private native offline archive under `.temp/module1-native-offline.zip`, with exact file hashes and existing learned artifacts. Not committed or redistributed; verify rights before sharing. CPU execution/requirements need isolated deployment verification before another hardware target is certified.

Measured native workstation evidence is in [metrics/module1-native-benchmark.json](metrics/module1-native-benchmark.json): Contact 105, tiled CPU, 12.504 seconds cold, three warm runs 2.509/2.504/2.735 seconds, sampled peak RSS 771,608,576 bytes (~736 MiB). The reported warm p95 is the nearest-rank statistic of only three samples, not a statistically stable production percentile. Power and exported-runtime equivalence are NOT_MEASURED/NOT_EVALUATED. Never infer viability on a 1 GB Oracle VM from this result; the control service is separate.

Survey job usage:

```powershell
python -B scripts/analyze_xtf.py path/to/survey.xtf --output-dir .temp/survey --rows 512 --overlap 64 --max-windows 10 --cancel-file .temp/survey.cancel
python -B scripts/analyze_xtf.py path/to/survey.xtf --output-dir .temp/survey --rows 512 --overlap 64 --max-windows 10 --cancel-file .temp/survey.cancel --resume
python -B scripts/benchmark_offline.py frontend/public/contact-105.jpg --runs 10 --device cpu --output .temp/device-benchmark.json
python -B scripts/package_offline.py --output .temp/private-offline-bundle.zip
```

Creating the cancellation file requests stop before the next inference window; remove it before a deliberate resume. Ctrl+C records cancellation. If a process is killed, the stale lock remains; verify it stopped before removing that lock. Resume requires identical source/configuration/artifact identities. `BOUNDED_COMPLETE` means the requested window cap was reached, not that the entire survey was processed. `contacts.json` uses sample-column/channel-row coordinates, not geographic metres; observations retain original window/candidate references.

### Explicit remaining gates

1. Survey log + configuration: real parser/rendering/channel/navigation verification; no synthetic test can close this.
2. Pose and reference locations: supported geometric/motion correction and field-error bounds. Geological survey logs alone may not provide debris labels or target ground truth.
3. Selected processing host and storage deployment: remote large-file jobs, proxy/TLS/persistence/backups, actual restored shared records and active admission settings. Local code/tests are not cloud activation.
4. Actual edge device/resources: target throughput/memory/power, compatible exported runtime comparison if required.
5. Coordinated HF/Vercel release: actual F8.1 response and correct source/exports. No production changes or live HF calls occurred.
6. Module 2: compatible fitted/calibrated policy and independent performance evaluation. Module 1 cannot establish 90% precision/recall.

Do not mark full Module 1 VERIFIED_DEPLOYED or all PS capabilities complete while these gates remain open. Available implementation is advanced locally; field, deployment and hardware completion remain separate.

Latest continuation gates: 40 frontend unit tests, ESLint, TypeScript, release build and built-asset credential scan passed. 21 backend tests passed, including the actual SQLite control API, team/image isolation, persistent admission, backup, job progress/resume/cancel and overlap mapping. Browser shared-pair restoration/report passed against a real temporary local service with no credential persistence or inference.


### Supabase + Vercel selected deployment

Supersedes the proposed Oracle hosting path for shared records/admission. Authenticated reviewers, private images, immutable AI records, append-only reviews, transactional global admission and scheduled expiry cleanup are implemented. See [SUPABASE_VERCEL_SETUP.md](SUPABASE_VERCEL_SETUP.md). Local release: 45 tests, lint/typecheck/build and asset credential scan passed. Embedded PostgreSQL checks cover migration, record/storage isolation, review conflicts, two-phase deletion and service-only admission. The mocked cloud browser flow restored a paired record, synced review revisions and preserved report source labels with no inference calls or page errors. Hosted schema/Auth/Storage/cron, production deployment and real live inference remain unverified. No HF inference quota consumed by these local checks.


### Real-data continuation — 3 October 2026

The user supplied the USGS 15CCT03 XTF survey and equipment documents. All 143 XTF logs have whole-file SHA-256 identities and bounded 32-ping sample parsing. Two CPU windows completed using existing artifacts, producing zero candidates; this is not an accuracy/background claim. Raw timestamp/channel/navigation/depth fields are preserved without invented alignment. Four windows prepared for human annotation with explicitly separate display-only previews. See [USGS_SURVEY_READINESS.md](USGS_SURVEY_READINESS.md) for all phase gates and training commands. No fitting/weight/policy changes occurred. Reference target positions, raw sample orientation, altitude reliability, motion correction, hosted jobs and edge gates remain open.


### Published deployment checks — 3 October 2026

Commits 3a809e1 and 3baf889 were pushed to GitHub main. Production public cloud configuration returned HTTP 200 for the selected project; public sign-ups are disabled and email login enabled. Unauthenticated records and maintenance return 401; foreign-origin inference returns 403. An isolated production browser completed verified example -> viewer -> report with preserved source labels, zero inference requests and zero page errors. See [production smoke evidence](metrics/supabase-production-smoke.json). Reviewer-authenticated save/restore, service-key admission RPC, scheduled cleanup and a corrected HF pipeline release remain unverified/not deployed. The initial records HTTP 500 was resolved by sharing plain ESM validation across browser/server. No GPU quota was consumed.
