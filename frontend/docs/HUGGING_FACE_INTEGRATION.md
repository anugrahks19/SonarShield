# Deployed Hugging Face integration

The production frontend connects to the public Gradio Space `mrintrovert19/sonar-shield-api`. Its published named analysis endpoint is `/analyze_image_gradio` with `image_filepath` and `run_tiled_auxiliary` inputs. The output is a JSON object in `result.data[0]`, validated against the frontend F8 analysis schema before display. The frontend never derives decisions, reliability, fusion, or localization.

The prior deployed Vercel bundle called `/predict`; the Space does not expose that endpoint. It also parsed the JSON output as a string and labeled all failures `API_OFFLINE`. The corrected adapter uses `handle_file(file)`, the named Gradio input object, and the actual endpoint. Endpoint mismatch, malformed output, and service failure now have distinct errors. The Space metadata being reachable is shown as `REACHABLE`; it does not prove model/component health or inference readiness.

The Space publishes no separate `/health`, `/detect`, `/report`, or human review endpoint. The report page renders the current validated analysis in the browser and provides JSON, CSV, and Print exports. Human review remains local to the browser. No generated backend report ID or component health is shown.

For Vercel, deploy the `frontend` directory as the project root with Vite build command `npm run build:release` and output directory `dist`. `VITE_GRADIO_SPACE_ID` may be set to `mrintrovert19/sonar-shield-api`; that is also the default. Keep `VITE_DEMO_MODE` and `VITE_USE_MOCK_DATA` false. `VITE_API_BASE_URL` is used only by legacy local FastAPI utilities and is not the deployed Gradio target. `vercel.json` rewrites client routes to `index.html`; static assets remain served directly.

After redeployment, check the deployed JavaScript no longer contains `/predict`, load `/analysis` directly, upload Contact 105, and confirm two candidates and boxes. Then check the browser console and network activity. A local production-preview browser test passed against the live Space on 2026-09-30; the existing Vercel bundle still contained `/predict` at that time and had not been redeployed.
