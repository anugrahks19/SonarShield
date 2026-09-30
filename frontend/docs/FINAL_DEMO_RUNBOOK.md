# Final demo runbook

Use the real F8 service for the primary demo. These steps assume the local setup in [DEPLOYMENT.md](DEPLOYMENT.md). The chosen Contact 105 image should be the actual QA input, not a synthetic upload.

1. Start backend: from the project root, run `python -B -m uvicorn ai.api.gate_f8_api_server:app --host 127.0.0.1 --port 8000` with the frozen runtime dependencies and artifacts available.
2. Start frontend: from `frontend`, run `npm install` then `npm run dev -- --host 127.0.0.1 --port 5173`; keep `VITE_DEMO_MODE=false` for the live path.
3. Verify `/health` at `http://127.0.0.1:8000/health` and the visible backend status in the app.
4. Load the real Contact 105 SSS image with the upload control and confirm its preview.
5. Run `/analyze` using **Run analysis** and wait for the real response. Do not present `/detect` as full analysis.
6. Select either of the two candidate rows and point to its box on the sonar viewer.
7. Explain the evidence fields that the backend actually supplied; call unavailable values unavailable.
8. Show the backend AI decision and source path. Contact 105's frozen example is REVIEW with GLOBAL and TILED candidates.
9. Show localization. Current F9 examples are pixel-only, so explain that a geographic marker needs valid backend coordinates.
10. Perform a human review, add a short note, and show the separate AI decision and human assessment labels.
11. Open the current analysis report and confirm both candidates appear.
12. Export JSON and CSV; optionally use browser Print to save a PDF.
13. Explain provenance as supplied by F8, and disclose that current API artifact hashes are placeholders pending a backend defect fix.
14. Stop. Close the demo without claiming a deployed production release.

## Backup demo path

If the live API is unavailable, **explicitly** restart Vite with `VITE_DEMO_MODE=true`, choose Contact 105 from **Load demo example**, and point out the **DEMO MODE** and **DEMO DATA** labels. The packaged example is a schema-valid pair of a real test image and frozen response; it is not a new inference request. The four examples are Contact 103, 104, 105, and background. Never describe demo data as live API output.
