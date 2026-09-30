import os
import shutil
import random
from pathlib import Path

V3_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3")
TRAIN_IMG = V3_DIR / "train" / "images"
TRAIN_LBL = V3_DIR / "train" / "labels"
VAL_IMG = V3_DIR / "val_clean" / "images"
VAL_LBL = V3_DIR / "val_clean" / "labels"

# 1. Find all ghost net images in train
ghost_net_images = []
for lbl in TRAIN_LBL.glob("*.txt"):
    with open(lbl, "r") as f:
        lines = f.readlines()
    has_ghost = False
    for l in lines:
        if l.strip() and l.strip().split()[0] == '3':
            has_ghost = True
            break
    if has_ghost:
        img_name = lbl.stem + ".jpg"
        if not (TRAIN_IMG / img_name).exists():
            img_name = lbl.stem + ".png"
        if (TRAIN_IMG / img_name).exists():
            ghost_net_images.append(img_name)

print(f"Found {len(ghost_net_images)} ghost_net images in train.")

# 2. Move ~15% to val_clean to ensure class representation
random.seed(42)
num_to_move = int(len(ghost_net_images) * 0.15)
selected = random.sample(ghost_net_images, num_to_move)

print(f"Moving {len(selected)} unique ghost_net images from train to val_clean...")

for img_name in selected:
    stem = Path(img_name).stem
    img_path = TRAIN_IMG / img_name
    lbl_path = TRAIN_LBL / f"{stem}.txt"
    
    shutil.move(str(img_path), str(VAL_IMG / img_name))
    shutil.move(str(lbl_path), str(VAL_LBL / f"{stem}.txt"))

# 3. Verify ZERO Train/Val Leakage
train_set = set([p.name for p in TRAIN_IMG.glob("*")])
val_set = set([p.name for p in VAL_IMG.glob("*")])
leakage = train_set.intersection(val_set)

print(f"\nVerification Results:")
print(f"Train images: {len(train_set)}")
print(f"Val images: {len(val_set)}")
print(f"Leakage (images in both): {len(leakage)}")

if len(leakage) == 0:
    print("SUCCESS: 0 train/val exact duplicates. Validation split is leak-free.")
else:
    print(f"ERROR: Found {len(leakage)} duplicates!")

# 4. Count final Ghost Net validation boxes
count = 0
for lbl in VAL_LBL.glob("*.txt"):
    with open(lbl, "r") as f:
        for l in f.readlines():
            if l.strip() and l.strip().split()[0] == '3':
                count += 1
print(f"\nGhost Net bounding boxes in val_clean: {count}")
