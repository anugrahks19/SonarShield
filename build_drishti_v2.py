import os
import glob
import cv2
import shutil
import hashlib
import random

# Paths
DRISHTI_V1_DIR = r"E:\GITHUB\a sih 2026\datasets\drishti_sss"
DRISHTI_V2_DIR = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2"
MILCO_DIR = r"E:\GITHUB\a sih 2026\datasets\MILCONOMBO Side-Scan Sonar Mine Dataset"
AI4_DIR = r"E:\GITHUB\a sih 2026\datasets\AI4Shipwrecks\AI4Shipwrecks"

# Helper to compute MD5 hash of a file
def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def create_dirs():
    for split in ['train', 'val']:
        os.makedirs(os.path.join(DRISHTI_V2_DIR, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(DRISHTI_V2_DIR, split, 'labels'), exist_ok=True)

def build_v2():
    create_dirs()
    seen_hashes = set()
    
    print("Step 1: Copying Base Drishti V1 into V2 and hashing...")
    for split in ['train', 'val']:
        v1_images = glob.glob(os.path.join(DRISHTI_V1_DIR, split, 'images', '*.*'))
        for img_path in v1_images:
            img_hash = get_file_hash(img_path)
            seen_hashes.add(img_hash)
            
            # Copy image
            basename = os.path.basename(img_path)
            dest_img = os.path.join(DRISHTI_V2_DIR, split, 'images', basename)
            shutil.copy2(img_path, dest_img)
            
            # Copy label
            label_name = os.path.splitext(basename)[0] + '.txt'
            src_label = os.path.join(DRISHTI_V1_DIR, split, 'labels', label_name)
            dest_label = os.path.join(DRISHTI_V2_DIR, split, 'labels', label_name)
            if os.path.exists(src_label):
                shutil.copy2(src_label, dest_label)

    print(f"Base dataset transferred. Unique images hashed: {len(seen_hashes)}")
    
    print("\nStep 2: Processing MILCO/NOMBO...")
    milco_added = 0
    milco_skipped = 0
    milco_images = []
    for ext in ['*.jpg', '*.png', '*.bmp']:
        for year in ['2010', '2015', '2017', '2018', '2021']:
            milco_images.extend(glob.glob(os.path.join(MILCO_DIR, year, year, ext)))
            
    for img_path in milco_images:
        img_hash = get_file_hash(img_path)
        if img_hash in seen_hashes:
            milco_skipped += 1
            continue
            
        seen_hashes.add(img_hash)
        milco_added += 1
        
        # Determine split (80/20)
        split = 'train' if random.random() < 0.8 else 'val'
        
        # Copy image
        basename = f"milco_{os.path.basename(img_path)}"
        dest_img = os.path.join(DRISHTI_V2_DIR, split, 'images', basename)
        shutil.copy2(img_path, dest_img)
        
        # Process label
        txt_path = os.path.splitext(img_path)[0] + '.txt'
        dest_label = os.path.join(DRISHTI_V2_DIR, split, 'labels', os.path.splitext(basename)[0] + '.txt')
        
        valid_lines = []
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                for line in f.readlines():
                    parts = line.strip().split()
                    if not parts: continue
                    cls_id = parts[0]
                    if cls_id == '0':  # MILCO -> mine_cylinder (4)
                        parts[0] = '4'
                        valid_lines.append(" ".join(parts))
                    elif cls_id == '1': # NOMBO -> ignore (background)
                        pass
                        
        with open(dest_label, 'w') as f:
            for line in valid_lines:
                f.write(line + '\n')
                
    print(f"MILCO/NOMBO -> Added: {milco_added}, Skipped (Duplicates): {milco_skipped}")

    print("\nStep 3: Processing AI4Shipwrecks...")
    ai4_added = 0
    ai4_skipped = 0
    ai4_masks = glob.glob(os.path.join(AI4_DIR, "*", "labels", "*.png"))
    
    for mask_path in ai4_masks:
        # The image path replaces /labels/ with /images/
        img_path = mask_path.replace('labels', 'images')
        if not os.path.exists(img_path):
            continue
            
        img_hash = get_file_hash(img_path)
        if img_hash in seen_hashes:
            ai4_skipped += 1
            continue
            
        seen_hashes.add(img_hash)
        ai4_added += 1
        
        split = 'train' if random.random() < 0.8 else 'val'
        
        basename = f"ai4_{os.path.basename(img_path)}"
        dest_img = os.path.join(DRISHTI_V2_DIR, split, 'images', basename)
        shutil.copy2(img_path, dest_img)
        
        dest_label = os.path.join(DRISHTI_V2_DIR, split, 'labels', os.path.splitext(basename)[0] + '.txt')
        
        # Convert mask to bbox
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        h, w = mask.shape
        points = cv2.findNonZero(mask)
        
        with open(dest_label, 'w') as f:
            if points is not None:
                # Get bounding box
                x, y, bw, bh = cv2.boundingRect(points)
                # Convert to YOLO format
                x_center = (x + bw / 2.0) / w
                y_center = (y + bh / 2.0) / h
                norm_w = bw / w
                norm_h = bh / h
                # class 2 is shipwreck
                f.write(f"2 {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}\n")
                
    print(f"AI4Shipwrecks -> Added: {ai4_added}, Skipped (Duplicates): {ai4_skipped}")
    
    # Create the drishti_v2.yaml
    yaml_content = f"""path: {DRISHTI_V2_DIR}
train: train/images
val: val/images

nc: 5
names:
  0: crab_pot
  1: submarine_pipeline
  2: shipwreck
  3: ghost_net
  4: mine_cylinder
"""
    with open(os.path.join(DRISHTI_V2_DIR, 'drishti_v2.yaml'), 'w') as f:
        f.write(yaml_content)
        
    print("\nDataset V2 Build Complete!")
    print(f"YAML config saved at: {os.path.join(DRISHTI_V2_DIR, 'drishti_v2.yaml')}")

if __name__ == "__main__":
    build_v2()
