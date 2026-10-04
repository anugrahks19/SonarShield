---
title: Sonar Shield API
emoji: 🦀
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.29.0
app_file: app.py
pinned: false
---

# SONAR-SHIELD live analysis backend

This ZeroGPU Space exposes `/analyze_image_gradio` for the Vercel interface. It uses the shared Module 1 runtime, the existing frozen V6 detector, and the existing D2 evidence-fusion artifact. This deployment does not train or replace weights.

The pipeline validates a JPEG/PNG, performs global and optional tiled detection, merges overlapping candidates by class, extracts acoustic evidence, and returns the F8.1 analysis contract. Image and model SHA-256 hashes are computed from actual bytes. Class IDs are checked against the detector checkpoint.

## Honest decision and location limits

Corrected results remain **REVIEW / uncalibrated** until compatible decision-policy and calibration artifacts are verified. Fusion scores are not calibrated probabilities. Geographic positions and estimated dimensions require a valid, image-bound `ground-range-raster-v1` metadata sidecar; ordinary uploads have pixel coordinates only. Raw XTF georeferencing and motion correction are not provided by this endpoint.

## Operation

ZeroGPU allocates hardware during the decorated inference function; an idle Space is not evidence of available inference quota. The Vercel gateway authenticates with a server-side HF token and all visitors share that account's finite quota. No token belongs in source code or a browser bundle. Verified frontend examples replay prior analyses without running inference. Shared records and review history are handled by Supabase/Vercel, not this Space.

Inputs: `image_filepath`, `run_tiled_auxiliary` (default true), `metadata_json` (default empty). Images are bounded to 32 MiB and 16 million pixels. Metadata is bounded to 256 KiB. Errors do not produce fabricated results.

Source: https://github.com/anugrahks19/SonarShield
Frontend: https://sonarshield26.vercel.app

Rollback: restore the previous Space commit and rebuild. Keep the frozen detector and fusion artifacts unchanged.
