# Deployment and local verification

## Local full-stack QA

Start the F8 server from the parent project root:

```powershell
python -B -m uvicorn ai.api.gate_f8_api_server:app --host 127.0.0.1 --port 8000
```

From `frontend`, run `npm ci`, then `npm run dev -- --host 127.0.0.1 --port 5173`. The development Vite proxy sends `/health`, `/detect`, `/analyze`, and `/report` to F8. For production-bundle local QA, set `VITE_API_BASE_URL=http://127.0.0.1:8000`, run `npm run build`, then `npm run preview -- --host 127.0.0.1 --port 4173`. This bundle is for local QA only.

## Production build

Set `VITE_API_BASE_URL` to the deployed **HTTPS origin** of F8, such as `https://api.example.invalid` replaced with the actual host. Set `VITE_DEMO_MODE=false` and `VITE_USE_MOCK_DATA=false`; omit either only when its default false is desired. Run `npm ci` and `npm run build:release`. This gate checks public configuration, lint, tests, TypeScript, and Vite output. Never place secrets in `VITE_*`; Vite embeds them in browser assets.

Publish `dist/` to a static frontend host with HTTPS. Rewrite frontend routes (`/analysis`, `/overview`, `/candidates`, `/reports`, `/system`) to `index.html`. The API calls use the configured F8 origin; route them to the FastAPI host, not the frontend SPA. Configure F8 CORS for the exact frontend origin and test a real browser upload. The current local F8 CORS response is `*`; production policy must be reviewed before publishing.

The app can use OpenStreetMap tiles by default. If the deployed network cannot reach that tile service, set both `VITE_MAP_TILE_URL` and `VITE_MAP_TILE_ATTRIBUTION` to an approved reachable service. Geographic markers still require actual F8 coordinates. If the API is down, the app shows OFFLINE and a retry action; it never silently substitutes demo data.

## Pre-release verification

1. Resolve the F9 source tag, calibration artifact, provenance placeholders, and reference mismatch in [RELEASE_AUDIT.md](RELEASE_AUDIT.md) through an authorized backend defect process.
2. Record the real frontend and F8 HTTPS URLs, deploy the API, then build and deploy the frontend using that exact F8 URL.
3. From a browser on the deployed frontend, check `/health`, upload Contact 103/104/105 and a background image, `/analyze`, viewer alignment, review, map empty/geographic states where data exists, report, JSON/CSV, print, console, and network/CORS.
4. Verify file-size limits, runtime/model loading, CPU/GPU behavior, logs without sensitive payloads, and backup of source/artifacts on the actual host.
5. Only after all gates pass, record the exact commit, lockfile, hashes, deployment hosts, and a clean tag. Do not publish the local `127.0.0.1` preview bundle.

No production or staging URLs were available on 2026-09-30, so deployment checks remain unverified.
