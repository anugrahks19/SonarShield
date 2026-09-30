# F9 Runtime Smoke Validation Report

The final end-to-end (E2E) runtime smoke validation has successfully passed. The script pushed 10 representative real Side Scan Sonar images (5 validation, 5 background) through the complete staged pipeline using the true production weights and logic.

## Proven Invariants

- **Decision Immutability:** If the frozen detector identifies a Wreck, D-2 Fusion assigns a fusion score, and Gate E produces a REVIEW decision, those outputs must remain unchanged through F8.
- **Component Integration:** The script successfully orchestrated the `TiledDetector`, `EvidenceExtractor`, `FusionPipeline` (with StandardScaler), and `DecisionEngine` without falling back to any mock stubs. 
- **Consistency:** `summary.candidate_count` and `summary` status sum match the actual `Candidate` count.
- **Identity mapping:** The output structure correctly maps against the F8 API schema definitions.
- **Schema Validation:** The `SeabedEvidence`, `ShadowEvidence`, and `QualityReport` successfully validated using the extracted sonar/image-derived feature values.
- **Data Provenance:** The `image_sha256` in provenance matched the input hash for every image.

## Spatial Distinction Audit (Contact_105)

During validation, `Contact_105` produced two Crab Pot candidates: one `GLOBAL` and one `TILED`. An audit was conducted to ensure these were not duplicate detections of the same physical target:

- **GLOBAL Candidate:** Bounding box center `(336.3, 15.5)`
- **TILED Candidate:** Bounding box center `(271.8, 426.7)`
- **Distance:** ~416 pixels. 

The `TILED` pipeline actually detected the `GLOBAL` target as well (IoU 0.85), but the spatial NMS correctly suppressed it. The second candidate corresponds to a genuinely distinct, spatially separated Crab Pot that the `GLOBAL` pass missed entirely. This provides a concrete runtime example of the auxiliary TILED path recovering a spatially distinct candidate missed by GLOBAL.

## Decision Vocabulary Resolution

The undocumented `LOW_EVIDENCE` status has been fully resolved. The `ScorePolicy` and `DecisionEngine` were updated to correctly output `REJECT` as the primary decision status, with `LOW_EVIDENCE` populated into the `reason_codes` list as intended by the Gate E architecture.

## Runtime Pipeline Output

```text
--- F9 Runtime Smoke Validation Results ---

[Contact_0_sslo_png_jpg.rf.4cb071a566c5fb06fd1f597700261198.jpg] -> 1 candidates
  - CAND-f4314336: Crab Pot   | REJECT       | Fusion: 0.452 | GLOBAL

[Contact_100_sslo_png_jpg.rf.0cdc1f62ac0c8580ad86b626c53b6374.jpg] -> 0 candidates

[Contact_103_sslo_png_jpg.rf.53fe66a3739b5f18e390901f89cf481e.jpg] -> 1 candidates
  - CAND-4ae62fad: Crab Pot   | REVIEW       | Fusion: 0.695 | TILED

[Contact_104_sslo_png_jpg.rf.22e4adfcabfab6cc53f6c4ec51d4099d.jpg] -> 1 candidates
  - CAND-7f896856: Crab Pot   | REVIEW       | Fusion: 0.751 | TILED

[Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg] -> 2 candidates
  - CAND-3a45c97a: Crab Pot   | REVIEW       | Fusion: 0.780 | GLOBAL
  - CAND-88483f73: Crab Pot   | REVIEW       | Fusion: 0.708 | TILED

[bg_1693569221.750_x1000.jpg] -> 0 candidates

[bg_1693569234.750_x2000.jpg] -> 0 candidates

[bg_1693569250.750_x1500.jpg] -> 0 candidates

[bg_1693569263.760_x500.jpg] -> 1 candidates
  - CAND-915bae94: Mine       | REVIEW       | Fusion: 0.699 | TILED

[bg_1693569310.770_x0.jpg] -> 0 candidates

✅ All F9 Runtime Invariants Passed!
```

## API Endpoint Validation (FastAPI)

To ensure the production API boundary functions correctly, a real HTTP POST request was made to the running FastAPI server (`/analyze`) using a raw Side Scan Sonar image via `multipart/form-data`. The server correctly routed the upload into the runtime pipeline and returned a valid F8 `AnalyzeResponse` JSON payload.

```text
Response Status Code: 200
Response Summary:
  Analysis ID: ANL-ef80c0f9
  Status: COMPLETED
  Candidate Count: 2
  Processing Time: 959 ms
First Candidate Snippet:
  Class: Crab Pot
  Decision: REVIEW
  Provenance image sha256: 6407b4344f90aa1ade206d83c2e9072e6a007c200f3a721212258908225e29e3
```

*Note: This 10-image validation is a runtime software smoke test intended to prove that the software stack actually runs end-to-end. Large-scale statistical model validation of the intelligence was conducted independently across earlier stages.*

## Status: Backend is Frozen 🔒

Backend intelligence and API contracts are frozen for product integration. Future changes are limited to defect fixes, security, performance, and integration issues; no model, evidence, threshold, or decision-policy changes are planned without reopening the relevant validation gate.

### Final Backend Status

```text
GATE A        ✅ FROZEN
GATE B        ✅ FROZEN
GATE C        ✅ FROZEN
GATE D-1      ✅ PASSED
GATE D-2      ✅ FROZEN
GATE E        ✅ FROZEN
F3            ✅ FROZEN
F4            ✅ VALIDATED
F5            ✅ VALIDATED
F6            ✅ FROZEN
F7            ✅ FROZEN
F8            ✅ FROZEN
F9            ✅ RUNTIME SMOKE PASSED
```

### Documented Limitations
- **Pipeline/Ghost:** Limited positive calibration evidence.
- **Sonar-relative/geographic coordinates:** Unavailable when metadata is absent.
- **Unknown:** Known-profile anomaly detection, not proof of a semantically unseen physical object.
