# M2.12 submission package

Prepared 4 October 2026. Software/documentation packaging completed. Archive CRC, all member hashes, pinned checkpoints and credential-pattern scans passed. No further training, new model promotion or production deployment is part of this phase.

## Contents

- Updated README and architecture/data-flow diagrams.
- Judge walkthrough, failure branch, local static backup and rollback instructions.
- Editable judge PowerPoint, factual metrics and future goals explicitly separated.
- M2.11 structured selection/verification evidence and frozen experimental manifest.
- Four paired examples and the built static frontend for a local HTTP-served backup.
- Frozen M2.08 experimental detector and preserved D1 baseline, individually hashed.
- Package manifest with SHA-256, size and source path for every member. No secrets, environment files, survey logs or training datasets are packaged.

Local output: `submission/m212_20261004/`. The package is a judge evidence/demo bundle, not a self-contained Python inference installation. The weights require the recorded trusted software environment. Static UI has no live gateway or cloud routes. Use the public website for those services.

## Release state

| Gate | Status |
|---|---|
| M2.11 local tests/build/browser checks | Passed within documented scope |
| M2.08 experimental artifact freeze | Complete, not deployed |
| 80% precision and 80% recall together | Not achieved |
| New detector compatible fusion/calibration | Not established |
| Independent annotated XTF field evaluation | Missing; public inference disabled |
| Fresh authenticated HF success in M2.11/12 | Not verified |
| Cloud note restoration and hosted SQL/maintenance | Previously user confirmed; no new full cloud check |
| Physical edge/AUV validation | Future milestone |

## Future accuracy work

Obtain confirmed real crab pots, wrecks, pipes, cylinders/nets and representative natural backgrounds; correct object boundaries and group related survey frames/crops. Reserve whole acquisition groups for independent calibration and final evaluation. Improve small-target localization and compare one controlled change at a time. Refit fusion for the selected detector's candidate protocol, calibrate supported scores and evaluate at one frozen operating point. Promote only after accuracy, artifact compatibility and viewer/report integration gates pass. No numerical improvement is guaranteed.

## Rebuild

From the repository root, after running `npm run build:release` from `frontend` and preparing the deck:

```powershell
python -B scripts/package_module2_submission.py --output submission/m212_20261004/rebuilt
```

The command refuses an existing output directory, pins checkpoint hashes and packages an explicit allowlist. It does not infer, train or deploy. Generated local binaries are not automatically committed. This phase's evidence must remain distinct from historical V6/fusion figures and the current website runtime.

## Completed verification

All eight final PPTX slides were rendered and inspected. Structural/layout/font checks passed, including two editable native tables. The extracted static frontend loaded all four paired examples and exported source-labelled reports in an isolated Edge browser with zero inference calls. This does not establish fresh production live success or independent model accuracy. [Packaging evidence](metrics/module2-m212-package-20261004.json).
