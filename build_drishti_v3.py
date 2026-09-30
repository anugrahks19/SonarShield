import os
import shutil
from pathlib import Path
import cv2
import yaml

# ============================================================
# CONFIG
# ============================================================

V1_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss")
V2_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2")
V3_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3")

CRAB_CROPS_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v3_crab_crops\images")
CRAB_CROPS_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v3_crab_crops\labels")

HN_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v3_hard_negatives\images")
HN_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v3_hard_negatives\labels")
NORM_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v3_normal_negatives\images")
NORM_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v3_normal_negatives\labels")

AI4_TRAIN = Path(r"E:\GITHUB\a sih 2026\datasets\AI4Shipwrecks\AI4Shipwrecks\train")
AI4_VAL = Path(r"E:\GITHUB\a sih 2026\datasets\AI4Shipwrecks\AI4Shipwrecks\val")

# Create V3 Directories
for split in ["train", "val", "test"]:
    (V3_DIR / split / "images").mkdir(parents=True, exist_ok=True)
    (V3_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. BASE: V1 DRISHTI
# ============================================================
print("Copying V1 Baseline...")
shutil.copytree(V1_DIR, V3_DIR, dirs_exist_ok=True)

# ============================================================
# 2. MILCO (MINES)
# ============================================================
print("Copying MILCO mines...")
for split in ["train", "val"]:
    milco_imgs = list((V2_DIR / split / "images").glob("milco_*"))
    for img in milco_imgs:
        shutil.copy(img, V3_DIR / split / "images" / img.name)
        lbl = V2_DIR / split / "labels" / f"{img.stem}.txt"
        if lbl.exists():
            shutil.copy(lbl, V3_DIR / split / "labels" / lbl.name)

# ============================================================
# 3. CLEANED AI4SHIPWRECKS
# ============================================================
print("Processing Cleaned AI4Shipwrecks...")
def process_ai4(ai4_dir, split_name):
    kept = 0
    masks = list((ai4_dir / "labels").glob("*.png"))
    for mask_path in masks:
        img_path = ai4_dir / "images" / mask_path.name
        if not img_path.exists(): continue
        
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None: continue
        h, w = mask.shape
        points = cv2.findNonZero(mask)
        if points is None: continue
        
        mask_area = cv2.countNonZero(mask)
        x, y, bw, bh = cv2.boundingRect(points)
        bbox_area = bw * bh
        if bbox_area == 0: continue
        
        mask_fill = mask_area / bbox_area
        bbox_ratio = bbox_area / (w * h)
        
        # 🔴 V3 FILTERING RULE (REMOVE PATHOLOGICAL BOXES)
        if bbox_ratio > 0.30 and mask_fill < 0.20:
            continue
            
        kept += 1
        out_stem = f"ai4_{img_path.stem}"
        shutil.copy(img_path, V3_DIR / split_name / "images" / f"{out_stem}.jpg")
        
        xc = (x + bw/2) / w
        yc = (y + bh/2) / h
        n_w = bw / w
        n_h = bh / h
        
        with open(V3_DIR / split_name / "labels" / f"{out_stem}.txt", "w") as f:
            f.write(f"2 {xc:.6f} {yc:.6f} {n_w:.6f} {n_h:.6f}\n")
    return kept

kept_train = process_ai4(AI4_TRAIN, "train")
kept_val = process_ai4(AI4_VAL, "val")
print(f"Kept {kept_train} train and {kept_val} val Shipwreck boxes.")

# ============================================================
# 4. CRAB POT CROPS
# ============================================================
print("Copying Crab Crops...")
for img in CRAB_CROPS_IMG.glob("*"):
    shutil.copy(img, V3_DIR / "train" / "images" / img.name)
for lbl in CRAB_CROPS_LBL.glob("*"):
    shutil.copy(lbl, V3_DIR / "train" / "labels" / lbl.name)

# ============================================================
# 5. NEGATIVES (BACKGROUNDS)
# ============================================================
print("Copying Curated Negatives & Benchmark...")
# Train Negatives
for img in HN_IMG.glob("*"):
    shutil.copy(img, V3_DIR / "train" / "images" / img.name)
for lbl in HN_LBL.glob("*"):
    shutil.copy(lbl, V3_DIR / "train" / "labels" / lbl.name)
for img in NORM_IMG.glob("*"):
    shutil.copy(img, V3_DIR / "train" / "images" / img.name)
for lbl in NORM_LBL.glob("*"):
    shutil.copy(lbl, V3_DIR / "train" / "labels" / lbl.name)

# Val Negatives (Untouched Benchmark) from V2
benchmark_count = 0
for lbl in (V2_DIR / "val" / "labels").glob("*.txt"):
    with open(lbl, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    if not lines:
        benchmark_count += 1
        shutil.copy(lbl, V3_DIR / "val" / "labels" / lbl.name)
        img = V2_DIR / "val" / "images" / (lbl.stem + ".jpg")
        if not img.exists():
            img = V2_DIR / "val" / "images" / (lbl.stem + ".png")
        if img.exists():
            shutil.copy(img, V3_DIR / "val" / "images" / img.name)
            
print(f"Copied {benchmark_count} untouched background images for validation benchmark.")

# ============================================================
# CREATE YAML
# ============================================================
with open(V1_DIR / "drishti.yaml", "r") as f:
    data = yaml.safe_load(f)
data["path"] = str(V3_DIR.absolute())
with open(V3_DIR / "drishti_v3.yaml", "w") as f:
    yaml.dump(data, f, sort_keys=False)

print("V3 DATASET ASSEMBLY COMPLETE!")
