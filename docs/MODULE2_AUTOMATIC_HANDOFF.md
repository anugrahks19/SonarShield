# M2.05 automatic screening → M2.06 handoff

Completed 3 October 2026. **M2.06 technical dataset preparation can proceed now. No training started.** This is automatic structural/provenance screening of inherited annotations, not expert ground truth certification.

## Results

| Check | Result |
|---|---:|
| Existing records and source identities checked | 13,342 |
| Retained inherited TRAIN candidates | 9,369 |
| Excluded TRAIN candidates | 2,844 |
| Historical DEV records preserved | 1,129 |
| Source annotations changed | 0 |
| Training/inference calls | 0 |

Retained boxes: crab-pot 8,757; pipeline 1,000; shipwreck 1,959; synthetic ghost-net 765; mine/cylinder inherited class 1,240. These counts establish retained label support only, not annotation completeness or accuracy.

Exclusion reasons overlap: 2,675 unconfirmed empty-label images, 10 identities already exposed across TRAIN/native TEST, and 464 image/parent cases in the capped protected-role similarity screen. Total unique exclusions are 2,844. Similarity cases are conservatively quarantined, not declared duplicates. All derived crops sharing a blocked parent are excluded by the same rule. Byte and existing decoded identities are deduplicated within the retained pool; historical role exposure is never reset.

Native crab TRAIN screen: 5,638 structurally valid, unharmonized source images; 83 invalid-bound images quarantined. These are not automatically appended to TRAIN: source mapping, actual acquisition identity, duplication and conflicting source licensing still matter. Existing inherited crab candidates remain explicitly inherited.

## Automatic decisions

- Reject malformed/out-of-bounds annotations instead of guessing corrected object boundaries.
- Exclude empty labels without confirmed target absence; do not convert unlabelled XTF/UXO imagery into negatives.
- Check image, label, crop-parent and source-label hashes against the pinned manifest; reject drift. Native metadata must still match the source audit.
- Block known historical TEST/background identities, current DEV identities, and protected crab filename families from TRAIN, including their crop parents.
- Keep mask semantics and MILCO/NOMBO hazard mapping unresolved; no AI guesses are written as approved labels.
- Preserve the historical DEV set for experiment comparisons, explicitly not an untouched final test.

## Artifacts

Private handoff: `.temp/module2-automatic-handoff-20261003-verified/`:

- `eligible-inherited-train.json`: retained candidate records with original hashes and annotation basis.
- `historical-dev.json`: unchanged DEV records.
- `exclusions.json`: per-image reason codes and parent identities.
- `summary.json`: input/output hashes, counts and readiness flags.

The earlier screening directory is preserved. The summary explicitly sets `training_ready=false`, `approved_dataset_ready=false`, and `expert_annotation_certification=false`. No fake human review decisions were generated. The manual review workspace remains optional for later experts; you do not need to process its entire queue to continue the technical workflow.

## M2.06 next

Construct a **new mechanically curated exploratory revision**, verify copies and manifests, retain inherited-label status, and generate class/size/source/split counts. Do not call that revision expert-approved or bypass guarded scientific readiness checks. Keep the baseline unchanged.

The retained list is positive-only because unconfirmed background images were excluded. This is **not a recommended final training mixture**: a builder should report the missing confirmed-negative pool, and later add verified hard backgrounds if available. Removing ambiguous negatives can reduce wrong supervision but can also hurt false-positive performance. No metric improvement follows automatically from this screening.

An AI can identify structural mistakes and propose likely boxes; it cannot establish hidden targets, absence of debris, acquisition independence or exact mask semantics from uncertain evidence. Missing expert evidence remains a limitation of accuracy certification and the public XTF gate; it does not prevent preparation of clearly labelled exploratory data.

## Verification

Five unit tests passed: protected-parent propagation, similarity-quarantine wording, empty-label exclusion, DEV/native-issue exclusion and source drift/class counts. The real screening verified pinned image/label/parent hashes for all 13,342 records. Source datasets, training runs, model weights and deployed inference were not modified. No training readiness or 80/90% performance claim is made.
