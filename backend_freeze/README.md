# Backend Freeze (F9 Checkpoint)

This directory records the intended F9 backend checkpoint. It is useful evidence for the project history, but it is **not currently a complete reproducible freeze**. See the [release audit](../frontend/docs/RELEASE_AUDIT.md) and [training limitations](../docs/TRAINING_AND_VALIDATION.md).

It contains:
- The `FREEZE_MANIFEST.json` defining the scope and models frozen.
- The `environment.json` recording the exact Python environment state.
- Hash records for detector, fusion, and policy artifacts; the calibration hash record is missing its file.
- The `f9_runtime_validation.md` report showing the full E2E execution results.

The Git tag `backend-freeze-f9` contains only this freeze metadata directory, not the full backend source. The recorded calibration hash is `FILE_NOT_FOUND`, so the full model/calibration integrity claim cannot be certified from this tag. The F9 runtime report is a ten-image end-to-end smoke check, not a field accuracy estimate.
