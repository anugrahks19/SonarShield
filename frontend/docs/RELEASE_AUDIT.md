# Phase 8 release audit — 2026-09-30

**Disposition: release blocked.** Local frontend and F8 integration are working. No production or staging URLs were provided, and the existing F9 Git tag and calibration reference do not establish a reproducible full-stack freeze. This audit is a release candidate record, not a final release certificate.

## Verified locally

| Gate | Result | Evidence |
| --- | --- | --- |
| TypeScript, lint, unit tests, production bundle | PASS | `npm run typecheck`, `npm run lint` (0 errors/warnings), `npm test` (21/21), `npm run build` |
| F8 health, detect, analyze, report | PASS with limitations | `python tests/phase8_api_smoke.py`: HTTP 200 for all four; `/detect` is a stub, `/report` has no served artifact |
| Real browser upload and analysis | PASS | `tests/browser_phase7.py`: Contact 103 and 104 each returned one candidate, Contact 105 returned two, background returned zero |
| Candidate viewer and bounding boxes | PASS | `tests/browser_phase4.py`: box position through zoom/pan, selection, direct CORS, no console/page/network errors |
| Review and AI/human separation | PASS locally | Phase 4 and 7 browser workflows; reviews live in browser storage, keyed by analysis and candidate |
| Map and localization | PASS for available data | `tests/browser_phase5.py`: real pixel-only response and schema-valid geographic/mixed fixtures; two and one fixture markers respectively; tile failure state |
| Report, JSON, CSV, print | PASS locally | `tests/browser_phase6.py`: two-candidate and zero-candidate paths, local review export, browser PDF print, no console errors |
| Responsive and offline UI | PASS | Production preview at 390×844 through 1920×1080, no horizontal overflow, offline state, 0 console/page errors |
| Explicit demo mode | PASS | `tests/browser_phase7_demo.py` uses four schema-valid frozen examples with `/analyze` blocked and DEMO DATA label |
| Production/staging deployment | UNVERIFIED | No deployment URLs exist yet |
| F9 source freeze and calibration | BLOCKED | See below |

## Test matrix

| Scenario | Input | Result |
| --- | --- | --- |
| Candidate-rich, multi-candidate, GLOBAL and TILED | Contact 105 live F8 | Two distinct candidates, viewer and report both show two |
| Single candidate, TILED, REVIEW | Contact 103/104 live F8 | One candidate each |
| Zero candidate | Background live F8 | Zero boxes, rows, review items and map markers |
| REJECT | Frozen F9 report documents Contact 0; browser UI fixture in Phase 4/6 | UI rendering tested with fixture; current live Contact 0 decision not independently checked in this Phase 8 run |
| UNKNOWN | Schema-valid Phase 4/6 fixture | UI only; no real UNKNOWN example available |
| Pixel-only and unavailable geography | Live F8 examples | No invented map marker |
| Geographic and mixed localization | Schema-valid Phase 5 fixture | Markers, selection, bounds and empty states tested; not a live geographic output |
| Uncertainty available/unavailable | Live response and schema-valid fixtures | Textual state rendered; no fabricated geographic radius |
| Human reviewed and unreviewed | Browser workflow | Separate from immutable AI decision; local review export tested |

The browser checks cover the principal workflow but do not certify every manual combination in the Phase 8 specification. Keyboard navigation, drag/drop, large upload rejection, rapid repeat clicks, backend recovery without refresh, and a visual review of every image aspect ratio still need a final operator pass on the deployed build. The Phase 4 script checks box coordinates after zoom and pan; it does not prove every detected target is scientifically correct.

## Backend freeze audit

The F9 manifest declares detector **V6-P2**, fusion **D2-v1**, decision policy **E1-v1**, calibration **F5-v1.0**. The detector, fusion, and policy files currently match their three recorded SHA-256 values. The calibration hash file says `FILE_NOT_FOUND`, and `ai/reliability/weights/f4_f5_calibration.json` is absent. Model/calibration integrity is therefore incomplete.

The root `backend-freeze-f9` tag contains only freeze metadata, not the backend and AI source claimed in `backend_freeze/README.md`. Its hash files contain placeholders, while the working tree has pre-existing modified freeze files and untracked backend/AI material. A clean comparison against that tag cannot be certified. The F8 server currently emits placeholder provenance hashes (`detector_hash`, `fusion_hash`, `policy_hash`, `calib_hash`). The published F9 validation report calls Contact 0 `REJECT`, while the checked-in runtime reference JSON contains `LOW_EVIDENCE`; that reference needs reconciliation. **No backend files were changed for Phase 8.**

The F8 API has no review endpoint. `/detect` returns a stub result. `/report` returns metadata with a URL reference, but fetching that path returned 404. Refresh clears the uploaded image and analysis response; local reviews reappear only when the same analysis ID and candidate IDs are loaded again. These are product limitations, not frontend-created backend results.

## Repository and release status

The requested `E:\GITHUB\a sih 2026\frontend` repository is on `main` with `origin` configured, but it contains the prior phase changes as unstaged/untracked files. Its tracked image audit found only a 13 KB starter `hero.png`; no tracked dataset or model file was found in this frontend repository. `.env.example` contains public placeholders, and no `.env*` file other than the example was found in this frontend directory. This does not certify a full parent-repository secret or large-file audit because the parent checkout has substantial untracked content.

The frontend package version is `1.0.0`. `package-lock.json` is present. A release-only build gate now requires a deployed HTTPS F8 origin and demo/mock flags disabled. The local preview bundle deliberately used `http://127.0.0.1:8000` for QA; it must never be uploaded as a production release. No final tag or `FINAL_RELEASE.md` was created. Before either is created, restore a trustworthy F9 source checkpoint and calibration artifact, replace placeholder provenance through an authorized backend defect fix, provide deployed URLs, run deployment QA, and commit a clean exact source state.

## Release blockers

1. No production or staging frontend/F8 deployment to verify HTTPS, production CORS, hosts, and inference.
2. `backend-freeze-f9` tag does not contain the claimed backend source; existing dirty/untracked backend state prevents freeze comparison.
3. Calibration artifact/hash is missing, so model/calibration integrity is not fully verifiable.
4. F8 provenance fields use placeholder artifact hashes.
5. Contact 0 reference decision conflicts with the F9 validation report and must be reconciled before the reference is used as release evidence.

The missing review endpoint, stub `/detect`, absent downloadable backend report, and refresh behavior remain documented limitations. If backend persistence or downloadable reports are required for release, they become additional backend work outside this frontend-only phase.
