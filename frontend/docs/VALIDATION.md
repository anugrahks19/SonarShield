# Validation scope and claims

This page summarizes repository evidence, not a new statistical validation. The project report at `../backend_freeze/f9_runtime_validation.md` records Gate A, B, C, D-1, D-2 and E as frozen/passed, F3/F6/F7/F8 as frozen, F4/F5 as validated, and F9 runtime smoke as passed. It describes ten real SSS images (five validation, five background) through the staged runtime and one FastAPI `/analyze` HTTP check. The underlying evaluation artifacts should be inspected separately before quoting performance metrics.

| Gate | Available evidence and boundary |
| --- | --- |
| A, B, C | Marked frozen in the F9 report; no Phase 8 revalidation of their datasets or metrics |
| D-1 | Marked passed; no new fusion thresholds or semantics were introduced in the frontend |
| D-2 | Marked frozen as fusion D2-v1 in the F9 manifest |
| E | Marked frozen as decision policy E1-v1 in the F9 manifest |
| F3 | Frozen adapter stage in the F9 report; frontend does not recalculate its output |
| F4 | Validated uncertainty stage in the F9 report; frontend renders supplied values only |
| F5 | Validated calibration stage in the report, but the current freeze calibration file is missing, so artifact integrity cannot be certified here |
| F6 | Frozen provenance/quality stage in the report; current F8 API emits placeholder artifact hashes and needs a defect fix |
| F7 | Frozen candidate contract in the report; current frontend validates and renders F7 fields without changing AI decisions |
| F8 | Frozen API contract in the report; local Phase 8 HTTP smoke passed `/health`, `/detect`, `/analyze`, `/report` with documented endpoint limitations |
| F9 | Ten-image runtime smoke is documented; repository tag/source and reference discrepancies prevent a clean Phase 8 freeze certification |

The F9 freeze manifest limits validated decision/fusion behavior to **Crab-Pot, Shipwreck, and Mine**. **Pipeline and Ghost-Net** remain review-only/uncalibrated within the frozen policy. Unknown is a known-profile anomaly signal, not proof of an unseen physical object. Geographic localization requires valid metadata; the current real examples are pixel-only. No accuracy, recall, latency SLA, or global coverage claim is established by the Phase 8 frontend checks.
