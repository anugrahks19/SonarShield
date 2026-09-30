import os
import shutil
from pathlib import Path
import yaml

V3_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3")
VAL_DIR = V3_DIR / "val"
VAL_CLEAN_IMG = V3_DIR / "val_clean" / "images"
VAL_CLEAN_LBL = V3_DIR / "val_clean" / "labels"
BENCHMARK_IMG = V3_DIR / "benchmark_bg" / "images"
BENCHMARK_LBL = V3_DIR / "benchmark_bg" / "labels"

for p in [VAL_CLEAN_IMG, VAL_CLEAN_LBL, BENCHMARK_IMG, BENCHMARK_LBL]:
    p.mkdir(parents=True, exist_ok=True)

# 1. Identify Leakage
train_imgs = set([p.name for p in (V3_DIR / "train" / "images").glob("*")])
val_imgs = set([p.name for p in (VAL_DIR / "images").glob("*")])
leakage = train_imgs.intersection(val_imgs)
print(f"Identified {len(leakage)} leaked train/val images.")

copied_clean = 0
copied_bg = 0

# 2. Separate into val_clean and benchmark_bg
for lbl in (VAL_DIR / "labels").glob("*.txt"):
    with open(lbl, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
        
    img_name = lbl.stem + ".jpg"
    if not (VAL_DIR / "images" / img_name).exists():
        img_name = lbl.stem + ".png"
        
    img_path = VAL_DIR / "images" / img_name
    
    if img_name in leakage:
        continue # Drop completely from all evaluation metrics
        
    if not lines:
        # Pure Background -> Independent FP Benchmark
        if img_path.exists():
            shutil.copy(img_path, BENCHMARK_IMG / img_name)
            shutil.copy(lbl, BENCHMARK_LBL / lbl.name)
            copied_bg += 1
    else:
        # Object Image -> Leak-free Evaluation/Validation Set
        if img_path.exists():
            shutil.copy(img_path, VAL_CLEAN_IMG / img_name)
            shutil.copy(lbl, VAL_CLEAN_LBL / lbl.name)
            copied_clean += 1

print(f"Val_clean: {copied_clean} object images.")
print(f"Benchmark: {copied_bg} background images.")

# 3. Update main yaml to point to val_clean
yaml_path = V3_DIR / "drishti_v3.yaml"
with open(yaml_path, "r") as f:
    data = yaml.safe_load(f)
data["val"] = "val_clean/images"
with open(yaml_path, "w") as f:
    yaml.dump(data, f, sort_keys=False)
print("Updated drishti_v3.yaml to point to val_clean.")

# 4. Create benchmark yaml for easy testing later
data["val"] = "benchmark_bg/images"
with open(V3_DIR / "drishti_v3_benchmark.yaml", "w") as f:
    yaml.dump(data, f, sort_keys=False)
print("Created drishti_v3_benchmark.yaml for isolated FP testing.")
