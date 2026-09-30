---
title: Sonar Shield API
emoji: 🦀
colorFrom: blue
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
---

# SONAR-SHIELD API

This folder contains the checked-in source used to package the **Gradio** Space. The active public endpoint is `/analyze_image_gradio`, decorated with `@spaces.GPU` for shared ZeroGPU inference. The frontend calls that named endpoint with `@gradio/client`; it does not call this repository's separate local FastAPI `/analyze` route.

The current public `app.py` and this checked-in copy still include placeholder input/provenance hashes and fixed reliability/localization-uncertainty values. They should be treated as an integration wrapper, not proof of measured end-to-end provenance. See the [architecture and limitations](../docs/ARCHITECTURE.md#important-hosted-wrapper-caveat) and the [project README](../README.md).
