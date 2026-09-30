import os
import random
import shutil
from pathlib import Path
from ultralytics import YOLO

# ============================================================
# CONFIG
# ============================================================

TRAIN_IMG_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\images")
TRAIN_LBL_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\labels")

OUT_HN_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v3_hard_negatives\images")
OUT_HN_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v3_hard_negatives\labels")
OUT_NORM_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v3_normal_negatives\images")
OUT_NORM_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v3_normal_negatives\labels")

for p in [OUT_HN_IMG, OUT_HN_LBL, OUT_NORM_IMG, OUT_NORM_LBL]:
    p.mkdir(parents=True, exist_ok=True)

# ============================================================
# IDENTIFY BACKGROUND IMAGES
# ============================================================

background_images = []
for lbl_path in TRAIN_LBL_DIR.glob("*.txt"):
    with open(lbl_path, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
        
    if not lines: # It's an empty label = background
        img_name = lbl_path.stem + ".jpg"
        if not (TRAIN_IMG_DIR / img_name).exists():
            img_name = lbl_path.stem + ".png"
            if not (TRAIN_IMG_DIR / img_name).exists():
                continue
        background_images.append((TRAIN_IMG_DIR / img_name, lbl_path))

print(f"Found {len(background_images)} total background images in training set.")

# ============================================================
# INFERENCE WITH V2-HN
# ============================================================

# We load V2-HN to see what it falsely detects
model = YOLO(r"E:\GITHUB\a sih 2026\models\v2\detector_v2_hn-4\weights\best.pt")

true_hard_negatives = []
normal_negatives = []

print("Running inference to mine Hard Negatives...")
for i, (img_path, lbl_path) in enumerate(background_images):
    # Run inference, silent mode
    results = model(str(img_path), verbose=False)
    
    # If model predicts at least one box on an empty background, it's a False Positive!
    if len(results[0].boxes) > 0:
        true_hard_negatives.append((img_path, lbl_path))
    else:
        normal_negatives.append((img_path, lbl_path))
        
    if (i + 1) % 500 == 0:
        print(f"Processed {i + 1}/{len(background_images)} backgrounds...")

print(f"Mined {len(true_hard_negatives)} TRUE Hard Negatives!")
print(f"Found {len(normal_negatives)} Normal Negatives.")

# ============================================================
# SAVE V3 NEGATIVES
# ============================================================

# We keep ALL True Hard Negatives
for img, lbl in true_hard_negatives:
    shutil.copy(img, OUT_HN_IMG / img.name)
    shutil.copy(lbl, OUT_HN_LBL / lbl.name)

# We curate a subset of Normal Negatives (e.g., 750)
random.seed(42)
selected_normal = random.sample(normal_negatives, min(750, len(normal_negatives)))
for img, lbl in selected_normal:
    shutil.copy(img, OUT_NORM_IMG / img.name)
    shutil.copy(lbl, OUT_NORM_LBL / lbl.name)

print(f"Saved {len(true_hard_negatives)} True Hard Negatives and {len(selected_normal)} Normal Negatives for V3.")
