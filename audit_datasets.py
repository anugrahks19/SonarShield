import os
import glob
import cv2
import numpy as np

MILCO_DIR = r"E:\GITHUB\a sih 2026\datasets\MILCONOMBO Side-Scan Sonar Mine Dataset"
AI4_DIR = r"E:\GITHUB\a sih 2026\datasets\AI4Shipwrecks\AI4Shipwrecks"
DRISHTI_DIR = r"E:\GITHUB\a sih 2026\datasets\drishti_sss"

def audit_milco():
    images = []
    for ext in ['*.jpg', '*.png', '*.bmp']:
        for year in ['2010', '2015', '2017', '2018', '2021']:
            images.extend(glob.glob(os.path.join(MILCO_DIR, year, year, ext)))
            
    milco_count = 0
    nombo_count = 0
    empty_count = 0
    
    for img_path in images:
        txt_path = os.path.splitext(img_path)[0] + '.txt'
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                lines = f.readlines()
                if not lines:
                    empty_count += 1
                for line in lines:
                    parts = line.strip().split()
                    if not parts: continue
                    cls_id = parts[0]
                    if cls_id == '0':
                        milco_count += 1
                    elif cls_id == '1':
                        nombo_count += 1
        else:
            empty_count += 1
            
    print("--- MILCO/NOMBO AUDIT ---")
    print(f"Total Images: {len(images)}")
    print(f"MILCO (0) Annotations: {milco_count}")
    print(f"NOMBO (1) Annotations: {nombo_count}")
    print(f"Images with no annotations (Background): {empty_count}\n")

def audit_ai4shipwrecks():
    train_masks = glob.glob(os.path.join(AI4_DIR, "train", "labels", "*.png"))
    test_masks = glob.glob(os.path.join(AI4_DIR, "test", "labels", "*.png"))
    all_masks = train_masks + test_masks
    
    empty_masks = 0
    for mask_path in all_masks:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is not None and cv2.countNonZero(mask) == 0:
            empty_masks += 1
            
    print("--- AI4Shipwrecks AUDIT ---")
    print(f"Total Images/Masks: {len(all_masks)}")
    print(f"Empty Masks: {empty_masks}\n")

def audit_drishti():
    labels = glob.glob(os.path.join(DRISHTI_DIR, "train", "labels", "*.txt")) + \
             glob.glob(os.path.join(DRISHTI_DIR, "val", "labels", "*.txt"))
             
    class_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    
    for label_path in labels:
        with open(label_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split()
                if not parts: continue
                cls_id = int(parts[0])
                if cls_id in class_counts:
                    class_counts[cls_id] += 1
                    
    print("--- DRISHTI V1 EXISTING ANNOTATIONS ---")
    print(f"crab_pot (0): {class_counts[0]}")
    print(f"submarine_pipeline (1): {class_counts[1]}")
    print(f"shipwreck (2): {class_counts[2]}")
    print(f"ghost_net (3): {class_counts[3]}")
    print(f"mine_cylinder (4): {class_counts[4]}\n")

if __name__ == "__main__":
    print("Starting Dataset Audit...\n")
    audit_milco()
    audit_ai4shipwrecks()
    audit_drishti()
