# M2.04 — source dataset audit

Technical audit completed 3 October 2026. **No source annotations, split files, model weights, deployment or training were changed.** Scientific approval remains pending: this module records eligibility and review needs rather than declaring every folder safe to train.

## Scope and reproducible evidence

- Indexed and SHA-256 hashed 116,686 raster entries across source/derived folders, excluding Git internals and AI4Shipwrecks paired mask rasters from the image count.
- Found 25,712 unique byte identities. Counts include review figures and derived revisions; neither number is an independent-scene count.
- Decoded 18,729 unique byte identities associated with primary sources, corrected data or Drishti V3; checked RGB pixel identity and bounded dHash similarity candidates. Other revision-only identities were byte-indexed, not fully decoded.
- Inventoried 143 raw XTF logs; their parser/field validation and annotations remain separate work.
- Saved current/native label structure, role, hashes, parent-path proxies and 20 saved training configurations. Acquisition/site/mission identity remains UNKNOWN where native records do not establish it.
- [Summary evidence](metrics/module2-source-audit-20261003.json). Full private artifacts: `.temp/module2-source-audit-20261003/` including inventory, exact groups, review queues, mask pairs, similarity candidates and native-test overlaps.

## 1. Source eligibility

| Source | Local image entries | Annotation findings | Decision for the next revision |
|---|---:|---|---|
| crab_pot | 6,674 | JSONL XYWH pixel boxes; 9,311 `Crab-Pot` objects; 83 images have bounds issues (85 offending boxes) | Confirm source pairing and review bounds; resolve license conflict before approved redistribution |
| AI4Shipwrecks | 251 | 251 masks paired; no dimension mismatches; 111 masks all black | Review mask foreground and object-instance semantics; do not equate fragments with separate wrecks or black masks with verified safe background |
| China Offshore | 3,255 | Image/folder categories; no detection boxes in local release | Annotation/negative-review queue, not ready-made detector labels |
| MILCONOMBO | 1,170 | Native classes 0 MILCO / 1 NOMBO; 436 structurally valid MILCO boxes, 231 NOMBO boxes; one malformed annotation; 866 empty labels | Preserve native distinction; validate mapping and review malformed/empty cases |
| SSS_UXO | 307 | No local annotations | Annotation queue only |
| controlled_v8a_20261003 | 13,342 | 12,213 TRAIN / 1,129 DEV; no structural label errors; 2,675 empty TRAIN labels | Preserve as exploratory reference; no new semantic/background or site-independence certification |

The crab-pot card advertises both `Crab-Pot` and `Maybe-Crab-Pot`, but the downloaded metadata contains **only `Crab-Pot`**. No current uncertain-category collapse was found by filename join. This does not certify every existing crab-pot label; geometry problems remain. The [publisher card](https://huggingface.co/datasets/PINGEcosystem/sss-crab-pot-detection-ds/blob/main/README.md) documents the native schema and ambiguity policy.

The native mine `obj.names.txt` supplies MILCO/NOMBO, and the [original publisher](https://figshare.com/articles/dataset/_i_Side-scan_sonar_imaging_for_Mine_detection_i_/24574879) confirms mine-like versus non-mine-like contacts. Neither label establishes cylinder shape, man-made origin for every NOMBO, or harmlessness. Do not automatically merge both into `mine_cylinder`. The malformed image is `2018/2018/0367_2018.jpg`, label line 2.

## 2. Historical roles and duplicate findings

- 13,739 exact-byte cross-role groups were found across the broad tree. **Most include historical aliases and repeated versions**; do not present this as 13,739 independent leakage incidents.
- **10 native AI4Shipwrecks TEST images occur byte-identically in current TRAIN.** They cannot be untouched final evidence. They include Artificial_Reef, Barge_No_1, Corsican, Lucinda_van_Valkenburg and WH_Gilbert images. Full identities are in `current-train-native-test-overlaps.json`.
- The corrected TRAIN/DEV exact-byte/pixel/parent safeguards from M2.01 remain intact. Source-native TEST overlap is a different, broader history check: the previous builder protected historical Drishti TEST, not every native source's original TEST.
- No cross-role decoded-pixel groups with *different byte identities* were found in the selected decode scope. This does not exclude visually similar, processed or adjacent-frame duplicates.
- No crab-pot filename families crossed its native train/validation/test paths under the `.rf`-suffix normalization. Actual survey/sequence groups remain unverified; different names can still originate from adjacent pings or the same target.
- Similarity screening reached its 20,000 candidate cap, with 5,680 crowded bucket events. 5,885 retained candidates involve current TRAIN together with a current/historical protected role. These are **review candidates**, not confirmed duplicates or confirmed leakage. `priority-near-review.json` lists them.

The near screen uses 64-bit dHash, four 16-bit bands and at most 32 prior identities per bucket, then Hamming distance <=4. It is deliberately bounded for repetitive seabed textures and cannot establish absence of near duplicates. Final disjointness requires acquisition grouping and reviewed candidates, not a hash threshold alone.

## 3. Structural and semantic review

Old V8-A has 12,401 declared TRAIN images plus 18 other raster entries. 141 TRAIN images fail the declared YOLO structure/geometry checks, and 18 non-TRAIN raster entries have no paired label. The previously documented hard-positive crop-label defect remains a reason to exclude that old revision from direct training; the corrected exploratory revision is separate.

Crab source bounds issues are **not automatically clipped**. A reviewer must inspect whether the box extends beyond a cropped raster intentionally, whether the coordinate conversion is wrong, or whether the annotation needs correction. Proposed decisions belong to a new revision with before/after provenance.

Shipwreck masks need native instance/site review. Full mask pairing found 111 all-black masks across local train/test/terrain inputs; this differs from the earlier 54-black count on the 141 TRAIN masks because the scope is larger. Native local image count is not inferred from the broader published dataset count.

China's local README explicitly states image-only recognition data without precise coordinates or survey-line identifiers. Its metadata split is for the image-level benchmark; path-derived role UNKNOWN in this audit is not a claim that its split CSV is absent. No detector training is authorized from a folder class alone. Preserve its explicit regions/categories and benchmark split during later annotation work.

The modified Drishti V3 tree contains class-0 annotations while its copied README says class 0 was omitted and describes a smaller original release. Therefore treat its documentation as upstream provenance clues, **not an accurate manifest of our modified tree**. It also documents synthetic ghost-net evaluation; real-net evidence is still missing.

## 4. License/provenance status

| Source | Evidence | Status |
|---|---|---|
| Crab pot | Local and live publisher metadata say CC-BY-SA-4.0; card body says GPL | CONFLICT — maintainer clarification needed; no fabricated verified license |
| Native MILCONOMBO | Original Figshare v2 lists CC BY 4.0 | Publisher terms identified; exact local archive checksums against publisher not verified |
| AI4Shipwrecks | Author project verified; dataset publisher returned HTTP 403; derived README claims CC-BY-4.0 | Primary dataset license still unverified here |
| China Offshore | Local README supplies citation/use context, no explicit grant identified | Upstream license verification required |
| SSS_UXO | Earlier audit claimed CC-BY-NC-SA; no primary terms verified in this module | Unverified |
| Drishti and derived versions | Copied README claims CC-BY-SA-4.0 with component attributions | Modified membership and component terms require reconciliation |

Primary references checked: [crab card](https://huggingface.co/datasets/PINGEcosystem/sss-crab-pot-detection-ds/blob/main/README.md), [native mine publisher](https://figshare.com/articles/dataset/_i_Side-scan_sonar_imaging_for_Mine_detection_i_/24574879), [AI4Shipwrecks author site](https://umfieldrobotics.github.io/ai4shipwrecks/), [SubPipe record](https://zenodo.org/records/10808161). SubPipe's retrieved page confirms SSS detector annotations and attribution text, but did not expose a license value. No messages were sent to maintainers.

## 5. M2.05 handoff

1. Review source bounds issues: 83 crab images and the native mine annotation.
2. Inspect shipwreck mask semantics/fragmented instances and 10 training-touched native-test cases; preserve the original files.
3. Review the protected-role similarity queue and build source site/sequence groups. Do not promote reviewed historical TEST into a supposedly fresh holdout.
4. Confirm natural-background negatives from the available imagery. Empty inherited labels alone do not establish target absence.
5. Decide supported semantic mapping for MILCO/NOMBO and China classes; obtain real net evidence or keep synthetic scope explicit.
6. Reconcile source rights and modified-dataset documentation before signing off the reviewed revision.

No new dataset is approved for training yet. **M2.04 technical source audit is complete; semantic review, license clarification, near-duplicate confirmation and independent acquisition groups are explicit handoff requirements.** These are not issues that more epochs can fix.
