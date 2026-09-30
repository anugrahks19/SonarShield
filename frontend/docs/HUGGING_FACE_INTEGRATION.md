# Deployed Hugging Face integration

The production frontend connects to the public Gradio Space `mrintrovert19/sonar-shield-api`. Its published named analysis endpoint is `/analyze_image_gradio` with `image_filepath` and `run_tiled_auxiliary` inputs. The output is a JSON object in `result.data[0]`, validated against the frontend F8 analysis schema before display. The frontend never derives decisions, reliability, fusion, or localization.

The prior deployed Vercel bundle called `/predict`; the Space does not expose that endpoint. It also parsed the JSON output as a string and labeled all failures `API_OFFLINE`. The corrected adapter uses `handle_file(file)`, the named Gradio input object, and the actual endpoint. Endpoint mismatch, malformed output, and service failure now have distinct errors. The Space metadata being reachable is shown as `REACHABLE`; it does not prove model/component health or inference readiness.

The Space publishes no separate `/health`, `/detect`, `/report`, or human review endpoint. The report page renders the current validated analysis in the browser and provides JSON, CSV, and Print exports. Human review remains local to the browser. No generated backend report ID or component health is shown.

## Judging when ZeroGPU is unavailable

The main path submits the uploaded image for live analysis and labels a successful response **LIVE ANALYSIS**. A reachable Space API does not mean ZeroGPU has capacity; the UI says **GPU UNVERIFIED** until a run succeeds, and a quota error is labeled **LIVE GPU LIMIT REACHED**. The uploaded image stays visible. The user may explicitly choose **View verified example** or **Try live again later**; there is no automatic fallback or retry.

The **Explore verified examples** button is available before any upload. Contact 105, 103, 104, and the zero-candidate background bundle real sample images with precomputed F9 responses. The frontend validates the response and checks each image SHA-256 before display. Example selection makes no Space inference request. The viewer, review area, report, print output, and downloaded JSON/CSV disclose **PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE**. This is a replay of the displayed sample, never an analysis of an uploaded image. The Oracle Micro VM is not used for inference.

For Vercel, deploy the `frontend` directory as the project root with Vite build command `npm run build:release` and output directory `dist`. `VITE_GRADIO_SPACE_ID` may be set to `mrintrovert19/sonar-shield-api`; that is also the default. Keep `VITE_DEMO_MODE` and `VITE_USE_MOCK_DATA` false. `VITE_API_BASE_URL` is used only by legacy local FastAPI utilities and is not the deployed Gradio target. `vercel.json` rewrites client routes to `index.html`; static assets remain served directly.

After redeployment, load `/analysis` directly, check the Space status says that GPU capacity is unverified, and open Contact 105 through **Explore verified examples**. Confirm two candidates and boxes, save a human review, inspect the report, and check the print and exports for the precomputed label. Then try a live upload when ZeroGPU capacity is available and confirm it is labeled **LIVE ANALYSIS**. Check the browser console and network activity. Run `python tests/browser_judge_fallback.py` against the local production preview on port 4182 for a no-inference offline walkthrough.
