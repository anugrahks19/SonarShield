# Real USGS survey: Module 1 and Module 2 readiness

Date: 3 October 2026. Source: user-provided `datasets/xtf` and FACS documents for USGS 2015-315-FA / 15CCT03. No training, calibration fitting, threshold selection or weight changes were performed.

## What was supplied and verified

- **143 XTF logs, 18,205,973,632 bytes** (18.21 GB decimal / approximately 16.96 GiB). The approximately 9 GB archive expands to this larger size. Two release metadata files are also present.
- The FACS overview says 144 XTF lines, but the release's completeness statement says 143. Local count agrees with the release; this discrepancy is recorded, not treated as missing data without a reference archive manifest.
- Equipment log: Klein 3900, SonarPro 12.1; release metadata says 455 kHz data was used. The XTF software header says `Klein 3000` / `KleinXlt`; header identity is retained and not silently overwritten by the documentation.
- Bounded sample audit: first 32 pings per file, two channels, unsigned 16-bit samples with 4,096 samples per channel row in inspected data. All files have complete SHA-256 hashes in [survey audit](metrics/usgs-15cct03-survey-audit.json). A prefix parse does not certify every payload in a file. Complete packet-boundary checks also passed all 143 logs: [framing audit](metrics/usgs-15cct03-framing.json). Vendor packets (including type 108) are counted and skipped, not interpreted as supported sonar data.
- XTF source references now retain raw record timestamps, timezone-unverified status, NavUnits code, channel type, ship and sensor coordinates, sensor depth and existing attitude/range fields. Zero/invalid timestamp fields remain unavailable. No coordinate or pose is fabricated.
- Existing V6 detector/fusion artifacts processed two 128-row CPU windows from the first log, retaining packet/ping and sample-column lineage. Both completed with zero candidates. This is a bounded processing test, not a clean-background label, whole-survey evaluation or proof of absence of debris.
- Four windows were exported for annotation. The full-scale previews are very dark; separate contrast previews are explicitly annotation-only. This confirms that raw-log rendering differs from the detector's image domain. No gain/CLAHE/denoising was enabled in model inference. Human boxes must retain the same pixel geometry; raw samples and source references remain authoritative.

## Navigation and geometry

The release documents WGS84 decimal-degree navigation and subsequent CleanSweep processing: offset/layback correction, bottom tracking, angle-varying gain and swath trimming before a 0.30 m mosaic. **That mosaic resolution does not apply to the raw XTF raster.** Chirp navigation files and chirp offset notes do not establish sidescan target accuracy.

The vessel diagram's Klein values are in centimetres: **20 cm forward, 185 cm starboard, tow depth -75 cm** relative to the documented convention. The Chirp's -160/-70/-85 cm values belong to a different sensor. Header offsets are zero in inspected samples and ship/sensor positions coincide, consistent with an uncorrected acquisition position; applying offsets twice must be avoided. The profile records these facts without activating an assumed transform.

Raw port and starboard sample arrays appear to have opposite near/far ordering, which requires confirmation before ground-range projection. Some inspected altitude values are around 51 m; the source describes a shallow estuary, so they require bottom-track review rather than blind conversion. Heading/pitch/roll values exist, but record presence does not verify pose timestamp alignment. Zero heave cannot be assumed to prove an absence of motion.

**No hazard pins or physical object dimensions are generated from these logs yet.** Actual target reference positions/extents, verified channel sample order, reliable altitude and pose alignment remain necessary to certify geographic error and motion correction.

## Phase status

| Phase | New evidence / work | Remaining gate |
|---|---|---|
| M1.08 | Real XTF navigation/attitude/range ingestion with raw timestamps and lineage | Confirm channel/time/pose semantics; image-sidecar path already exists |
| M1.09 | Documented WGS84 and survey lever-arm profile | Ground-range conversion from these raw samples and reference-target field error are unverified |
| M1.10 | All-file identities and bounded real parsing; two-window CPU job | Complete semantic payload inspection (framing already verified), validated rendering and large-job hosted execution |
| M1.11 | Real sample quality/pose inspection and preserved originals | Validated bottom tracking, motion correction and field reference transforms |
| M1.12 | Supabase SQL applied and Vercel variables configured by user; code locally tested | Deploy current source and test actual cloud Auth/Storage/admission/cron |
| M1.13 | Existing workstation CPU benchmark plus real-log smoke | Actual target edge hardware, exported-runtime equivalence and power |
| M1.14 | Local regressions; survey-specific limitations documented | Hosted release and remaining survey/hardware gates |
| M2.01 | New survey identity/provenance, whole-file hashes, one acquisition group | Previous training pools/pretraining, crops and near duplicates still need broader audit |
| M2.02 | Guarded training preflight checks hashes, human-verification state, explicit labels and group-disjoint roles | Reviewed labels, enough independent acquisition groups, frozen evaluator/protocol and final test scope |
| M2.03-M2.10 | No training or promotions performed | Prerequisite annotations/splits/baselines/calibration and independent evaluation |

All 143 logs belong to the same field activity. Random window splits across its lines do not establish independent final evidence. These are **unlabelled geological survey observations**, not a five-class hazard benchmark and not verified negative data. Model predictions may help propose regions for review, but must not become ground truth without independent human verification.

## Commands you can run

PowerShell uses `Set-Location`, not `cd /d`. Install optional raw dependencies in the existing isolated test target if absent:

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -m pip install --target .temp/module1-pyxtf --no-deps pyxtf==1.4.2
$env:PYTHONPATH = 'E:\GITHUB\a sih 2026\.temp\module1-pyxtf'
python -B scripts/audit_survey.py datasets/xtf --output-dir .temp/survey-audit-new --hash-files
python -B scripts/verify_xtf_framing.py datasets/xtf --output .temp/survey-framing-new.json
python -B scripts/prepare_survey_annotations.py datasets/xtf/15CCT03_SSS_150528172600.xtf --output-dir .temp/annotation-batch-new --max-windows 4
```

Choose new output directories; annotation export rejects overwriting existing work. Use an annotation tool to mark true classes and boxes, including explicit reviewed backgrounds. Classes: 0 crab_pot, 1 submarine_pipeline, 2 shipwreck, 3 ghost_net, 4 mine_cylinder. Do not invent labels for unfamiliar contacts. Confirm rendering/orientation before large-scale annotation.

### Training: commands only, not ready to run against this unlabelled survey

The existing `ai/train_v8_a.py` effective YAML still points `val` at `drishti_sss_v3/test/images`. Its printed preflight uses `val_clean`, but that printout does not change the YAML passed to Ultralytics. Preserve the existing exploratory run; do not cite it as untouched final-test evidence or launch another run with that YAML.

After approved annotations and split audit, create `datasets/approved_sonar/data.yaml` with TRAIN and separate DEV image directories, and `datasets/approved_sonar/split-manifest.csv` with **absolute image paths**, split (`TRAIN`, `DEV`, `CALIB`, `FINAL_TEST` or `HISTORICAL_TEST`), acquisition_group, annotation_status=`HUMAN_VERIFIED`, and the actual image SHA-256. Use standard `images/train`, `images/val`, `labels/train`, `labels/val` layout. Every training/DEV image needs an explicit reviewed label file, including empty files only for verified backgrounds.

First run a preflight only:

```powershell
python -B scripts/train_guarded.py --data datasets/approved_sonar/data.yaml --manifest datasets/approved_sonar/split-manifest.csv --weights models/v6/detector_v6_p2_sss/weights/best.pt --dry-run
```

Once that passes **and the broader provenance/evaluation review is complete**, you may start training yourself:

```powershell
python -B scripts/train_guarded.py --data datasets/approved_sonar/data.yaml --manifest datasets/approved_sonar/split-manifest.csv --weights models/v6/detector_v6_p2_sss/weights/best.pt --epochs 80 --device 0 --project models/controlled --name survey_candidate_01 --execute
```

These approved paths are a future dataset, not files already populated with labels. The launcher does not fit parameters without `--execute`; it blocks invalid/protected splits, changed hashes, missing/unreviewed labels and acquisition-group leakage. It does not certify source rights, unknown pretraining overlap or near-duplicate independence. Epoch count and new raw data do not guarantee 90% precision and recall; those require measured results at the same frozen operating point on independently labelled data.

## Cloud next step

Deploy the tested source after following [Supabase setup](SUPABASE_VERCEL_SETUP.md). Environment values alone cannot add the new API endpoints. The 18 GB raw corpus must remain local or on a separately designed job-storage service; the eight-record Supabase configuration is for bounded image/result pairs, not raw survey archives. Vercel's inference gateway accepts a small HF file reference, not raw XTF uploads.

Source attribution: [USGS release metadata](https://cmgds.marine.usgs.gov/catalog/spcmsc/GrandBay_2015-315-FA_metadata.faq.html), local metadata TXT/XML, three FACS Word documents and supplied vessel diagram. USGS release declares public-domain data with attribution requested.

Local regression results: 25 backend/preflight tests passed. The current V8 YAML was deliberately rejected by the guarded dry-run for pointing validation at test data; no model was loaded or trained by that rejected preflight.

Production frontend update: source was published to main; public Supabase config and offline example/report browser smoke passed. Cloud reviewer persistence and service-key/cron behavior remain separate unverified production gates.
