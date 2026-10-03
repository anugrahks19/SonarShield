# Corrected exploratory training revision

Prepared 3 October 2026. No training was started by the agent. Existing datasets, checkpoints and runs were preserved.

The new ignored local dataset is `datasets/controlled_v8a_20261003`: 11,339 accepted original training images plus 874 regenerated positive crops (12,213 total), and 1,129 DEV images. 193 source/crop candidates were excluded for invalid annotations, duplicates, protected overlap, or excluded/unmatched parents. These counts are entries, not independent survey scenes.

The crop-label bug was caused by replacing every `.jpg` occurrence in a filename such as `crop_v8a_mine_0066_2015.jpg_gt_3.jpg`, producing a label basename different from the loader's expected final-suffix pairing. The new builder uses `Path.with_suffix('.txt')`, regenerates crops from hash-matched parent images, verifies the selected class and GT, and projects **all visible source boxes** into the cropped raster. Fractional positive extents are preserved instead of rounded to zero. Invalid parent boxes are excluded rather than silently clipped or semantically relabelled. Previously generated empty crop labels are not copied into the new revision.

DEV uses the accepted `val_clean` pool, never the historical `test` directory. Exact-byte and decoded-pixel overlaps with historical TEST/background are excluded; cross-TRAIN/DEV exact byte/pixel duplicates and shared crop parents are blocked. The launcher pins image, label, parent, source-label, YAML, manifest and V6 starting-weight hashes. It requires class support in both roles and rejects changed or unmanifested inputs, mismatched label basenames and empty hard-positive crops. There is no automatic production promotion.

## Start on the available Windows RTX 4060

```powershell
Set-Location 'E:\GITHUB\a sih 2026'
python -B scripts/train_corrected_candidate.py --execute
```

Default: V6-P2 starting weights, 80 epochs, 640 pixels, batch 8, GPU 0, AdamW, seed 0, deterministic, Windows workers 0, early stopping patience 20. Output is `models/controlled/v8a_labels_fixed_01`; an existing run directory is never overwritten. Running the command without `--execute` only verifies the dataset. Preparation can be reproduced in a fresh directory with `scripts/prepare_corrected_candidate.py --output <new-directory>` and that directory passed to the launcher with `--dataset`.

## Scientific boundary

This is a corrected **exploratory training revision**, not completion of Module 2 or certified labels/splits. Original labels are inherited source annotations; geometric reconstruction is not new expert semantic review. Empty original annotations remain inherited backgrounds, not newly confirmed negatives. Site/mission grouping and near-duplicate independence still require review; DEV is historically used and is not an untouched final holdout. The XTF images remain unlabelled and are excluded. The strict `train_guarded.py` scientific workflow remains unchanged; this separately named launcher explicitly records its exploratory scope instead of fabricating HUMAN_VERIFIED statuses.

A training run does not guarantee 90% precision/recall or establish XTF accuracy. After the run, compare DEV candidates, refit compatible fusion/calibration if justified, freeze an operating point and evaluate untouched independently labelled external/XTF data. Only then consider public XTF integration. Existing deployed model artifacts are unchanged until that reviewed promotion.
