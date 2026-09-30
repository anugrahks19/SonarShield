import shutil
from pathlib import Path
import yaml

V3_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3")
V4_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v4")
HP_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v4_hard_positives\images")
HP_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v4_hard_positives\labels")

print("Copying V3 base to V4...")
shutil.copytree(V3_DIR, V4_DIR, dirs_exist_ok=True)

print("Adding Multi-Scale Hard Positives to V4 train...")
added_imgs = 0
for img in HP_IMG.glob("*.jpg"):
    shutil.copy(img, V4_DIR / "train" / "images" / img.name)
    added_imgs += 1
for lbl in HP_LBL.glob("*.txt"):
    shutil.copy(lbl, V4_DIR / "train" / "labels" / lbl.name)
    
print(f"Added {added_imgs} Hard Positive crops.")

yaml_path = V4_DIR / "drishti_v4.yaml"
with open(V3_DIR / "drishti_v3.yaml", "r") as f:
    data = yaml.safe_load(f)
data["path"] = str(V4_DIR.absolute())
with open(yaml_path, "w") as f:
    yaml.dump(data, f, sort_keys=False)

print("V4 DATASET BUILD COMPLETE!")
