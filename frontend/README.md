# SONAR-SHIELD frontend implementation notes

For the current judge-facing overview, architecture, training evidence, limitations, and setup, start at the [repository README](../README.md). Some lower sections here retain the historical local FastAPI phase workflow; the hosted frontend uses the Gradio endpoint described below.

## Judge walkthrough: live first, verified example when needed

**Live** processes the judge's uploaded JPG or PNG now through the Hugging Face Space. A successful result is labeled **LIVE ANALYSIS**. ZeroGPU is shared and may refuse a run even when the Space API is reachable. When its quota is reached, the uploaded image stays visible, the app explains the limit, and the judge can explicitly choose **View verified example** or **Try live again later**. There is no automatic retry or switch to sample data.

**Verified example** replays a previously completed F9 analysis of the displayed sample image. It makes no new inference and never represents an uploaded image. **Explore verified examples** is available before any upload and works while the Space is offline. Contact 105 is the default; Contact 103, Contact 104, and the zero-candidate background are also bundled. The app checks each image SHA-256 against its saved response before loading. Candidate selection, evidence, human review, localization, and reports remain interactive. The viewer, review area, report, print view, and downloaded files are labeled **PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE**. The Oracle Micro VM is not used for inference or as a quota workaround.

**Current hosted integration:** Vercel calls the Hugging Face Gradio Space `mrintrovert19/sonar-shield-api` through `/analyze_image_gradio`. See [Hugging Face integration and redeployment](docs/HUGGING_FACE_INTEGRATION.md). The sections below describe the original local FastAPI F8 workflow and its historical QA; they do not describe the current hosted API transport.

The analysis workspace renders an F8-shaped response from the current Gradio adapter (or a verified F9 example), provides a separate human review workflow, and displays backend geographic coordinates in Leaflet when available. It does not calculate candidate decisions, fusion, reliability, or location.

**Current status:** the public Vercel frontend and Gradio Space are deployed, and the frontend's offline, quota, and mocked live paths have been checked. The historical [Phase 8 release audit](docs/RELEASE_AUDIT.md) predates that deployment; its F9 freeze/provenance blockers still matter. No final full-stack release certificate has been issued.

Run `npm install` and `npm run dev` from this directory. Run `npm test` for the contract and viewer checks and `npm run build` for TypeScript validation plus the Vite production build. The active analysis adapter connects to the configured Hugging Face Space.

**Run analysis** submits the selected JPG or PNG file to the Space's `/analyze_image_gradio` endpoint. The four frozen F9 runtime examples use the same validated renderer and do not call the Space.

The deployed Space exposes no separate health, raw detection, report, or review endpoint. The workspace uses the returned F8/F7-shaped analysis for the viewer and browser report. The frontend labels backend-supplied reliability and localization uncertainty without reinterpretation.

## API configuration

Copy `.env.example` to `.env.local` only if you need to override the default public Space ID. `VITE_GRADIO_SPACE_ID` defaults to `mrintrovert19/sonar-shield-api` and must use `owner/space` syntax. The legacy `VITE_API_BASE_URL` is not used by the hosted Gradio analysis adapter. These variables contain public configuration only.

The normal workflow calls the real Space analysis endpoint. The verified examples are available in release builds through an explicit chooser, with source labels throughout. `VITE_DEMO_MODE=true` adds a development-only DEMO MODE badge; leave it false for release. API failures never trigger a sample fallback automatically.

For deployment, set the public Space ID if different from the default. The Vercel route rewrites in `vercel.json` serve `index.html` for frontend paths such as `/reports/:analysisId`. `VITE_*` values are bundled into browser code, so never put credentials in them. Build with `npm run build:release` and deploy `dist/`.

For a release build, use `npm run build:release`. It verifies the Space identifier, rejects demo/mock mode, and runs lint, unit tests, TypeScript, and the bundle build. See [Hugging Face deployment instructions](docs/HUGGING_FACE_INTEGRATION.md).

Responses are checked against the F7/F8 shape before rendering. The service indicator checks Space API reachability on startup and can be retried; it is not a model health check. Stale analysis responses are ignored when the user changes input or the app unmounts.

## Viewer controls

- **FIT** keeps the complete image within the viewer. **1:1** uses one screen pixel per image pixel. **RESET** returns to fit with no pan.
- Use **+ / −** or the mouse wheel to zoom. Drag the image to pan when enlarged. **BOXES ON/OFF** changes overlay visibility only.
- Boxes use the untouched F8 `detection.bbox` pixel coordinates. The image and boxes share one screen transform: `screen = centered image offset + pan + image pixel × display scale`. Selecting a box or result row centers that candidate when the image is larger than the viewer.
- The cursor readout is in image pixels. It is not a geographic location.

The candidate strip keeps backend order. Up and Down move selection between visible rows; Enter or Space selects a focused row. Filters change only the displayed list.

## Human review

F8 has no review or feedback endpoint. Human assessments are stored only in this browser under `sonarShield.review.v1`, keyed by both `analysis_id` and `candidate_id`. The stored record contains the assessment, exact reviewer note, and local timestamp; it does not contain sonar images or change F7/F8 candidate objects. A new backend analysis ID does not inherit an earlier analysis's review. Clearing browser storage removes local reviews. Reloading the same analysis response restores its matching reviews, although the frontend does not persist the analysis response or uploaded image across page refreshes.

Choose **Confirmed**, **False positive**, or **Needs investigation**, add a note, and select **Save review**. A confirmation dialog shows the original AI class and decision beside the human assessment. **Reset review** also requires confirmation and removes only the local review. The queue shows human review progress and deterministic next/previous or next unreviewed navigation. Its AI and human filters are separate; review counts are workflow counts, not model metrics.

For a live browser smoke check while Vite and F8 are running, run `python tests/browser_phase4.py`. It checks direct browser CORS, real upload, box alignment through zoom and pan, review persistence and reset, zero candidates, responsive layout, and console errors. Its three-candidate REJECT/UNKNOWN scenario is a browser test fixture; normal analysis continues to call the real F8 API.

## Geospatial workspace

The map reads `candidate.localization` directly. Only candidates with backend status `GEOGRAPHIC` and valid WGS84 latitude/longitude get Leaflet markers. Pixel and sonar coordinates appear in labeled detail sections; they are never converted into geographic coordinates. The current frozen F9 examples are all `PIXEL_ONLY`, so real uploads show an honest map-unavailable state. The F7/F8 contract has no survey track or geographic uncertainty region. Its class-conditional pixel uncertainty remains textual and is never drawn as a map radius.

Map markers, sonar boxes, the candidate list, and the inspection panel share the same selected candidate ID. Clicking a marker pans to it; selecting from the list or sonar viewer highlights its marker without taking over the map viewport. A new analysis replaces old map data. Missing tiles show a warning while coordinate text remains available. The default basemap uses OpenStreetMap tiles with attribution; set `VITE_MAP_TILE_URL` and `VITE_MAP_TILE_ATTRIBUTION` together to use another provider. Deployment must provide access to the chosen tile service or replace it with an approved internal source.

For live and fixture-based browser verification, run `python tests/browser_phase5.py` while Vite and F8 are running. Geographic, mixed, and invalid examples in that script are test fixtures; they are not application data.

## Reports and exports

Open **Reports** after an analysis to view its input record, original or annotated sonar image, candidate details, evidence, localization, quality flags, provenance, and separately labeled local human reviews. The report is a projection of the current F8 `/analyze` response. It is session-only: a refresh clears the analysis response and uploaded image. No persistent history is available.

**Export JSON** downloads the complete F8 analysis unchanged under `analysis` and matching local reviews under `human_review`. **Export CSV** writes one row per candidate; unavailable coordinates are blank, including in zero-candidate results (header only). **Print report** uses the browser's print dialog, where users can save a PDF. There is no separate PDF generator.

**Request F8 report metadata** calls the frozen `/report` endpoint for the current analysis ID. The endpoint returns a report ID, status, and URL reference but does not serve a downloadable report artifact. The frontend displays that reference as text. JSON and CSV downloads are generated from the current validated analysis response in the browser.

Run `python tests/browser_phase6.py` while Vite and F8 are running for live upload, report request, JSON/CSV, print, responsive layout, and zero-candidate verification. Its geographic UNKNOWN/REJECT scenario is a browser test fixture. `npm test` checks export fidelity and safe filenames.

## Phase 7 interface

The landing route `/` and `/analysis` show the sonar workspace. `/overview` summarizes the current session, `/candidates` opens the workspace at the review queue, `/reports` and `/reports/:analysisId` show the current session report, and `/system` shows F8 health. Browser history and direct URLs work. A direct report URL after refresh shows an unavailable state because F8 does not provide analysis history. The Vite proxy forwards only exact F8 API paths, so `/reports` remains a frontend route.

On desktop the sidebar stays compact; on narrow screens its menu button opens a drawer. Candidate selection is shared by the sonar viewer, queue, inspection panel, and map. The panel has previous and next controls. When focus is outside interactive controls, Left and Right select adjacent candidates; `?` opens shortcut help. Review confirmation accepts Escape. A top-level error boundary offers reload if rendering fails. Notifications report analysis, review, and export actions without changing backend records.

For current hosted-integration QA, run `python tests/browser_judge_fallback.py` and `python tests/browser_mock_gradio.py` against a production preview on port 4182. The first blocks the Space, opens all four verified examples, completes human review and report exports, checks print output, then verifies that an offline live failure keeps the uploaded image and requires explicit fallback selection. The second simulates a ZeroGPU quota response and a successful live response without calling ZeroGPU. Historical FastAPI checks remain in `browser_phase7.py` and `browser_phase7_demo.py`.

## Release and validation documents

- [Release audit and blockers](docs/RELEASE_AUDIT.md)
- [Deployment and environment](docs/DEPLOYMENT.md)
- [Validation scope](docs/VALIDATION.md)
- [14-step demo runbook](docs/FINAL_DEMO_RUNBOOK.md)
- [3–5 minute demo script](docs/DEMO_SCRIPT.md)
- [Machine-readable release candidate record](docs/RELEASE_CANDIDATE.json)
