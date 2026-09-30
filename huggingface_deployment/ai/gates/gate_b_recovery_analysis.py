import os
import cv2
import json
import torch
from pathlib import Path
from tqdm import tqdm
from torchvision.ops import box_iou
import pandas as pd

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector

def calculate_recovery():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    val_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images"
    val_lbl_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\labels"
    
    # Use standard operational threshold for testing candidate recovery
    detector = TiledDetector(model_path, conf=0.15, iou=0.7)
    
    images = [f for f in os.listdir(val_img_dir) if f.endswith(('.jpg', '.png'))]
    
    results_list = []
    
    for img_file in tqdm(images, desc="Running Recovery Analysis"):
        img_path = os.path.join(val_img_dir, img_file)
        lbl_path = os.path.join(val_lbl_dir, img_file.rsplit('.', 1)[0] + '.txt')
        
        image = cv2.imread(img_path)
        img_h, img_w = image.shape[:2]
        
        gt_boxes = []
        gt_labels = []
        if os.path.exists(lbl_path):
            with open(lbl_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        cls_id = int(parts[0])
                        x_c, y_c, w, h = map(float, parts[1:])
                        x1 = (x_c - w/2) * img_w
                        y1 = (y_c - h/2) * img_h
                        x2 = (x_c + w/2) * img_w
                        y2 = (y_c + h/2) * img_h
                        gt_boxes.append([x1, y1, x2, y2])
                        gt_labels.append(cls_id)
                        
        if not gt_boxes:
            continue
            
        gt_boxes_t = torch.tensor(gt_boxes)
        
        preds_global = detector.predict(image, trigger_conf=-1.0)
        preds_tiled = detector.predict(image, trigger_conf=2.0)
        preds_hybrid = detector.predict(image, trigger_conf=0.15)
        
        def match_gt(preds):
            if not preds:
                return [False] * len(gt_boxes)
            pred_boxes_t = torch.tensor([p["bbox"] for p in preds])
            pred_classes = [p["class"] for p in preds]
            ious = box_iou(gt_boxes_t, pred_boxes_t)
            
            matches = []
            for i in range(len(gt_boxes)):
                matched = False
                for j in range(len(preds)):
                    if ious[i, j] > 0.5 and gt_labels[i] == pred_classes[j]:
                        matched = True
                        break
                matches.append(matched)
            return matches
            
        match_g = match_gt(preds_global)
        match_t = match_gt(preds_tiled)
        match_h = match_gt(preds_hybrid)
        
        for i in range(len(gt_boxes)):
            results_list.append({
                "image_id": img_file,
                "class": gt_labels[i],
                "global_detected": match_g[i],
                "tiled_detected": match_t[i],
                "hybrid_detected": match_h[i]
            })
            
    df = pd.DataFrame(results_list)
    df.to_csv(r"E:\GITHUB\a sih 2026\ai\reference\gate_b_recovery.csv", index=False)
    
    print("\n--- Recovery Analysis ---")
    classes = {0: "Crab", 1: "Pipe", 2: "Wreck", 3: "Ghost", 4: "Mine"}
    for c_id, c_name in classes.items():
        sub_df = df[df["class"] == c_id]
        if len(sub_df) == 0:
            continue
            
        missed_by_global = sub_df[~sub_df["global_detected"]]
        tiled_recovery = missed_by_global["tiled_detected"].sum()
        hybrid_recovery = missed_by_global["hybrid_detected"].sum()
        
        print(f"\n{c_name} (Total instances: {len(sub_df)})")
        print(f"  Missed by GLOBAL: {len(missed_by_global)}")
        print(f"  Recovered by TILED: {tiled_recovery} ({tiled_recovery/len(missed_by_global)*100:.1f}% of misses if > 0)")
        print(f"  Recovered by HYBRID: {hybrid_recovery} ({hybrid_recovery/len(missed_by_global)*100:.1f}% of misses if > 0)")

if __name__ == "__main__":
    calculate_recovery()
