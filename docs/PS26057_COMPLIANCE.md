## Latest release boundary — 4 October 2026

M2.11 local QA passed 47 frontend, 52 backend and four freeze tests, 12 metric reconciliations and five browser scenarios. M2.12 packages this evidence. New M2.08 weights are experimental and not deployed; 80/80 remains unmet. Public XTF, independent geometry/motion validation and compatible calibration remain open. [Final release report](MODULE2_M211_RELEASE.md) · [Submission package](MODULE2_M212_SUBMISSION.md). The requirement boundaries below still apply.

# PS 26057: current prototype compliance

Updated 3 October 2026. Software changes do not retrain the detector or justify a new accuracy claim. This is a prototype, not certified survey or cleanup navigation.

| Requirement | Working implementation and evidence | Remaining boundary |
| --- | --- | --- |
| Detect man-made sonar objects with boxes or masks | Frozen five-class detector provides boxes, tiled processing and inspectable evidence; shipwreck, pipeline, ghost net, mine/cylinder and crab pot classes | No segmentation model is claimed; external generalization and calibrated performance need Module 2 |
| Confidence and false-positive reduction | Detector confidence and separate evidence-fusion score are presented/exported; raw reports include 0–100% detector-score presentation | Scores are not calibrated probabilities; incompatible policy/calibration stays unavailable and machine decisions stay REVIEW |
| Speckle, acoustic shadows, variable resolution | Existing shadow/texture/geometric evidence and bounded tiled detector; recorded deterministic log/percentile raw rendering, geometry source checks and quality warnings | No proof of robustness across all noise/resolution/acquisition domains; changing rendering or filters needs independent evaluation |
| Raw sonar ingestion | Browser upload and bounded local CPU XTF processing, private local persistence/cancel/resume, generated image/evidence/review/report workflow; full supported-payload decode across 143 logs | Only supported XTF representation; vendor packets, unsupported sample formats and other raw formats rejected; Vercel remains JPG/PNG/small-record gateway |
| Navigation metadata | Source-bound profile, units/timezone/channel/pose/altitude and sensor/GPS distinction validated; optional metadata upload | Real sensor orientation, synchronized vertical solution and survey configuration require verification |
| Latitude/longitude and physical dimensions | WGS84 candidate projection and estimated dimensions when reviewed geometry is supplied; geographic display and JSON/CSV/GeoJSON | Exact hazard locations/sizes cannot be claimed without independent measured contacts; absent geometry stays unavailable |
| Heave/pitch/roll/data dropouts | Per-ping yaw, pose-rotated lever arm and bounded flat-bottom slant correction; unsafe motion rejected, dropout intersections exposed, no made-up fill | Full beam/terrain and independently aligned heave correction not implemented/validated; M1.11 remains partial |
| Dashboard/report downloads | Vercel upload/live viewer, map when coordinates exist, candidate evidence, human review, reports/CSV/JSON/print, paired complete-record import/export; local raw dashboard/offline geographic viewer | Batch CPU/HF queue time is not guaranteed real-time operation; no cloud-generated PDF artifact |
| Authenticated durable records | User verified cloud save/open and same review note after refresh; Supabase user isolation/private images/immutable revisions | Client-imported analysis is not server-certified original inference evidence |
| Resource/abuse controls | Five hosted SQL checks passed; shared admission/daily budget/lease boundaries; server-only secrets; manual maintenance invocations HTTP 200 | Finite HF service-account quota; automatic cron occurrence and actual expired-image deletion not directly observed |
| Lightweight offline/edge operation | Native private offline bundle, actual Windows CPU full-pipeline timing/RSS and private ONNX raw-tensor comparison | No Raspberry Pi/Jetson/drone benchmark or power measurement; tensor comparison is not full exported-pipeline accuracy validation |

## Latest additions: independent raw review and future edge API

162 blind annotation windows from 28 logs over seven days have been prepared: 116 DEV, 22 CALIBRATION, 24 TEST. Whole-day separation reduces adjacent-window leakage; these remain one unlabelled survey, not independent external field evidence. The frozen class-correct evaluator blocks unreviewed data and reports object precision/recall, not system accuracy. Public raw inference is still gated. See [review instructions and release criteria](XTF_ACCURACY_RELEASE.md).

An authenticated, bounded local [edge-device image API](EDGE_DEVICE_API.md) returns the existing F8 analysis contract. A real CPU request returned HTTP 200 with verified frozen artifact hashes and REVIEW-only decisions; no training or HF quota was consumed. This is not an AUV hardware certification.

## Current evidence gates

47 frontend/server tests, 43 backend/preflight tests, embedded PostgreSQL isolation/admission/retention checks, release lint/typecheck/build/secret-pattern scan, live-response rendering and mocked cloud roundtrip, user-confirmed hosted cloud roundtrip, real local raw upload/report browser walkthrough and synthetic geographic interaction passed. No HF inference calls or training were required for this closure task.

## What cannot be closed by coding alone

1. Known target locations/dimensions and independently reviewed source geometry for real-survey accuracy.
2. Verified beam/pose/vertical conventions and independent acquisition references for full motion correction. This also requires further processing implementation; it is not merely a missing test.
3. Physical edge-device certification is deferred at the user's request. The new authenticated image API supplies a future integration contract; real device throughput, power and vehicle compatibility remain unmeasured.
4. Independent labeled validation and verified calibration in Module 2 for precision/recall or 90% claims.

Module 1 remains partially open on field accuracy/full-motion processing and public XTF validation. Physical edge certification is a future milestone rather than a required present prototype gate. Hosted records and database usage controls now have real evidence. See [release commands and detailed evidence](MODULE1_RELEASE_20261003.md).

The original full-scale XTF rendering was defective for low-amplitude UINT16 samples. It was corrected after a user visual report; the exact log now has a visible image and a real-candidate review/export walkthrough. Candidate counts do not establish field accuracy. See the release report for legacy-preview pairing and corrected-run evidence.
