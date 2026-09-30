import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from torchvision.ops import box_iou

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector

def plot_boxes(img, boxes, color, title=""):
    img_copy = img.copy()
    if len(img_copy.shape) == 2:
        img_copy = cv2.cvtColor(img_copy, cv2.COLOR_GRAY2RGB)
    for b in boxes:
        x1, y1, x2, y2 = map(int, b)
        cv2.rectangle(img_copy, (x1, y1), (x2, y2), color, 4)
    return img_copy

def generate_audit():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    val_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images"
    val_lbl_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\labels"
    bg_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images"
    
    out_dir = r"E:\GITHUB\a sih 2026\ai\reference\gate_b_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    detector = TiledDetector(model_path, conf=0.15, iou=0.7)
    
    # 1. Targets (A & B)
    images = [f for f in os.listdir(val_img_dir) if f.endswith(('.jpg', '.png'))]
    
    recovered_count = 0
    rejected_count = 0
    new_fp_count = 0
    
    def get_matches(preds, gt_boxes_t, gt_labels):
        if not preds:
            return [False] * len(gt_boxes_t)
        pred_boxes_t = torch.tensor([p["bbox"] for p in preds])
        pred_classes = [p["class"] for p in preds]
        ious = box_iou(gt_boxes_t, pred_boxes_t)
        
        matches = []
        for i in range(len(gt_boxes_t)):
            matched = False
            for j in range(len(preds)):
                if ious[i, j] > 0.5 and gt_labels[i] == pred_classes[j]:
                    matched = True
                    break
            matches.append(matched)
        return matches
    
    for img_file in images:
        if recovered_count >= 5 and rejected_count >= 5:
            break
            
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
            
        preds_g = detector.predict(image, trigger_conf=-1.0)
        preds_t = detector.predict(image, trigger_conf=2.0)
        
        gt_boxes_t = torch.tensor(gt_boxes)
        match_g = get_matches(preds_g, gt_boxes_t, gt_labels)
        match_t = get_matches(preds_t, gt_boxes_t, gt_labels)
        
        boxes_g = [p["bbox"] for p in preds_g]
        boxes_t = [p["bbox"] for p in preds_t]
        
        for i in range(len(gt_boxes)):
            g_hit = match_g[i]
            t_hit = match_t[i]
            
            if not g_hit and t_hit and recovered_count < 5:
                # Case A: Global miss, Tiled hit ON THIS SPECIFIC OBJECT
                # Focus the plot specifically on the recovered object
                obj_box = [gt_boxes[i]]
                fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
                ax1.imshow(plot_boxes(image, obj_box, (0, 255, 0)))
                ax1.set_title("Ground Truth (Green)")
                ax2.imshow(plot_boxes(image, boxes_g, (255, 0, 0)))
                ax2.set_title("GLOBAL: MISS (Red = Preds)")
                ax3.imshow(plot_boxes(image, boxes_t, (0, 0, 255)))
                ax3.set_title("TILED: RECOVERED (Blue = Preds)")
                plt.savefig(os.path.join(out_dir, f"A_recovered_{recovered_count}.jpg"))
                plt.close()
                recovered_count += 1
                
            elif g_hit and not t_hit and rejected_count < 5:
                # Case B: Global hit, Tiled miss ON THIS SPECIFIC OBJECT
                obj_box = [gt_boxes[i]]
                fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
                ax1.imshow(plot_boxes(image, obj_box, (0, 255, 0)))
                ax1.set_title("Ground Truth (Green)")
                ax2.imshow(plot_boxes(image, boxes_g, (0, 0, 255)))
                ax2.set_title("GLOBAL: HIT (Blue = Preds)")
                ax3.imshow(plot_boxes(image, boxes_t, (255, 0, 0)))
                ax3.set_title("TILED: MISSED (Red = Preds)")
                plt.savefig(os.path.join(out_dir, f"B_rejected_{rejected_count}.jpg"))
                plt.close()
                rejected_count += 1

    # 2. Backgrounds (C)
    bg_images = [f for f in os.listdir(bg_img_dir) if f.endswith(('.jpg', '.png'))]
    for img_file in bg_images:
        if new_fp_count >= 5:
            break
            
        img_path = os.path.join(bg_img_dir, img_file)
        image = cv2.imread(img_path)
        
        preds_g = detector.predict(image, trigger_conf=-1.0)
        preds_t = detector.predict(image, trigger_conf=2.0)
        
        boxes_g = [p["bbox"] for p in preds_g]
        boxes_t = [p["bbox"] for p in preds_t]
        
        # New FP means an FP by TILED that was NOT found by GLOBAL.
        # We just check if TILED has more boxes, or if there's any box in TILED not overlapping with GLOBAL
        if len(boxes_t) > len(boxes_g):
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
            ax1.imshow(plot_boxes(image, boxes_g, (0, 0, 255)))
            ax1.set_title("GLOBAL: Prev FPs (Blue)")
            ax2.imshow(plot_boxes(image, boxes_t, (255, 0, 0)))
            ax2.set_title("TILED: New FP (Red)")
            plt.savefig(os.path.join(out_dir, f"C_new_fp_{new_fp_count}.jpg"))
            plt.close()
            new_fp_count += 1

    print("Visual audit generation complete. Check ai/reference/gate_b_audit/")

if __name__ == "__main__":
    generate_audit()
