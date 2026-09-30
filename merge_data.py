import os
import shutil
import glob

src_base = r"E:\GITHUB\a sih 2026\datasets\crab_pot"
dst_base = r"E:\GITHUB\a sih 2026\datasets\drishti_sss"

splits = {"train": "train", "valid": "val", "test": "test"}

for src_split, dst_split in splits.items():
    src_dir = os.path.join(src_base, src_split)
    if not os.path.exists(src_dir): continue

    dst_img_dir = os.path.join(dst_base, dst_split, "images")
    dst_lbl_dir = os.path.join(dst_base, dst_split, "labels")
    os.makedirs(dst_img_dir, exist_ok=True)
    os.makedirs(dst_lbl_dir, exist_ok=True)
    
    jpgs = glob.glob(os.path.join(src_dir, "**", "*.jpg"), recursive=True)
    txts = glob.glob(os.path.join(src_dir, "**", "*.txt"), recursive=True)
    txts = [t for t in txts if not t.endswith("classes.txt") and not t.endswith("readme.txt")]
    
    print(f"Merging {src_split} -> {dst_split} ({len(jpgs)} imgs, {len(txts)} labels)")
    
    for f in jpgs:
        shutil.copy(f, dst_img_dir)
    for f in txts:
        # Force class 0 (crab_pot) just in case the original dataset used a different ID
        with open(f, 'r') as file:
            lines = file.readlines()
        
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) > 0:
                parts[0] = '0' # force class 0 for crab_pot
                new_lines.append(" ".join(parts))
                
        with open(os.path.join(dst_lbl_dir, os.path.basename(f)), 'w') as file:
            file.write("\n".join(new_lines) + "\n")

print("Merge complete!")
