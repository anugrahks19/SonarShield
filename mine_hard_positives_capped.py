import os
import cv2
import yaml
import shutil
import random
import numpy as np
import math
from pathlib import Path
from ultralytics import YOLO

def box_iou(box1, box2):
    b1_x1, b1_y1 = box1[0] - box1[2]/2, box1[1] - box1[3]/2
    b1_x2, b1_y2 = box1[0] + box1[2]/2, box1[1] + box1[3]/2
    b2_x1, b2_y1 = box2[0] - box2[2]/2, box2[1] - box2[3]/2
    b2_x2, b2_y2 = box2[0] + box2[2]/2, box2[1] + box2[3]/2
    
    inter_x1 = max(b1_x1, b2_x1)
    inter_y1 = max(b1_y1, b2_y1)
    inter_x2 = min(b1_x2, b2_x2)
    inter_y2 = min(b1_y2, b2_y2)
    
    if inter_x2 < inter_x1 or inter_y2 < inter_y1:
        return 0.0
        
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    b1_area = box1[2] * box1[3]
    b2_area = box2[2] * box2[3]
    
    iou = inter_area / (b1_area + b2_area - inter_area)
    return iou

def main():
    V3_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3")
    TRAIN_IMG = V3_DIR / "train" / "images"
    TRAIN_LBL = V3_DIR / "train" / "labels"
    
    V4_HP_IMG = Path(r"E:\GITHUB\a sih 2026\datasets\v4_hard_positives\images")
    V4_HP_LBL = Path(r"E:\GITHUB\a sih 2026\datasets\v4_hard_positives\labels")
    
    if V4_HP_IMG.exists():
        shutil.rmtree(V4_HP_IMG)
    if V4_HP_LBL.exists():
        shutil.rmtree(V4_HP_LBL)
        
    V4_HP_IMG.mkdir(parents=True, exist_ok=True)
    V4_HP_LBL.mkdir(parents=True, exist_ok=True)
    
    model = YOLO(r"E:\GITHUB\a sih 2026\models\v3\detector_v3-2\weights\best.pt")
    
    target_classes = {0, 2, 4} # crab, shipwreck, mine
    max_hp = {0: 500, 2: 300, 4: 200}
    hp_counts = {0: 0, 2: 0, 4: 0}
    
    MAX_HARD_CROPS_PER_SOURCE = 6
    scales = [1.3, 1.8, 2.5]
    
    images = list(TRAIN_IMG.glob("*"))
    random.seed(42)
    random.shuffle(images)
    
    crops_generated = 0
    audit_samples = {0: [], 2: [], 4: []}
    class_confusion = 0
    
    print("Mining Hard Positives with source-capping and auditing...")
    
    for idx, img_path in enumerate(images):
        lbl_path = TRAIN_LBL / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            continue
            
        with open(lbl_path, "r") as f:
            gt_lines = [l.strip().split() for l in f.readlines() if l.strip()]
            
        if not gt_lines: continue
        
        has_target = False
        for gt in gt_lines:
            c = int(gt[0])
            if c in target_classes and hp_counts[c] < max_hp[c]:
                has_target = True
                break
                
        if not has_target:
            continue
            
        res = model(str(img_path), conf=0.1, verbose=False)
        pred_boxes = res[0].boxes
        
        preds = []
        for box in pred_boxes:
            c = int(box.cls.item())
            x, y, w, h = box.xywhn[0].tolist()
            preds.append((c, [x, y, w, h]))
            
        img = None
        source_crops = 0
        
        for gt_idx, gt in enumerate(gt_lines):
            if source_crops >= MAX_HARD_CROPS_PER_SOURCE:
                break
                
            c = int(gt[0])
            if c not in target_classes or hp_counts[c] >= max_hp[c]:
                continue
                
            gx, gy, gw, gh = map(float, gt[1:5])
            gt_box = [gx, gy, gw, gh]
            
            best_iou_correct_class = 0.0
            best_iou_any_class = 0.0
            best_pred_class = -1
            
            for pc, pbox in preds:
                iou = box_iou(gt_box, pbox)
                if iou > best_iou_any_class:
                    best_iou_any_class = iou
                    best_pred_class = pc
                if pc == c and iou > best_iou_correct_class:
                    best_iou_correct_class = iou
                    
            if best_iou_any_class > 0.5 and best_pred_class != c:
                class_confusion += 1
                
            if best_iou_correct_class < 0.5:
                hp_counts[c] += 1
                
                if img is None:
                    img = cv2.imread(str(img_path))
                    if img is None: break
                    ih, iw = img.shape[:2]
                
                for scale in scales:
                    if source_crops >= MAX_HARD_CROPS_PER_SOURCE:
                        break
                        
                    crop_w = int(gw * iw * scale)
                    crop_h = int(gh * ih * scale)
                    crop_w = max(crop_w, 100)
                    crop_h = max(crop_h, 100)
                    
                    cx = int(gx * iw)
                    cy = int(gy * ih)
                    
                    x1 = max(0, cx - crop_w // 2)
                    y1 = max(0, cy - crop_h // 2)
                    x2 = min(iw, cx + crop_w // 2)
                    y2 = min(ih, cy + crop_h // 2)
                    
                    crop_img = img[y1:y2, x1:x2].copy()
                    if crop_img.shape[0] < 10 or crop_img.shape[1] < 10:
                        continue
                        
                    c_iw = x2 - x1
                    c_ih = y2 - y1
                    new_cx = cx - x1
                    new_cy = cy - y1
                    new_gw = gw * iw
                    new_gh = gh * ih
                    n_cx = min(max(new_cx / c_iw, 0), 1)
                    n_cy = min(max(new_cy / c_ih, 0), 1)
                    n_w = min(new_gw / c_iw, 1)
                    n_h = min(new_gh / c_ih, 1)
                    
                    out_stem = f"{img_path.stem}_hp_{gt_idx}_s{int(scale*10)}"
                    cv2.imwrite(str(V4_HP_IMG / f"{out_stem}.jpg"), crop_img)
                    
                    with open(V4_HP_LBL / f"{out_stem}.txt", "w") as f:
                        f.write(f"{c} {n_cx:.6f} {n_cy:.6f} {n_w:.6f} {n_h:.6f}\n")
                        
                    crops_generated += 1
                    source_crops += 1
                    
                    if scale == 1.8:
                        if (c == 0 and len(audit_samples[0]) < 50) or \
                           (c == 2 and len(audit_samples[2]) < 25) or \
                           (c == 4 and len(audit_samples[4]) < 25):
                            
                            bx1 = int((n_cx - n_w/2) * c_iw)
                            by1 = int((n_cy - n_h/2) * c_ih)
                            bx2 = int((n_cx + n_w/2) * c_iw)
                            by2 = int((n_cy + n_h/2) * c_ih)
                            cv2.rectangle(crop_img, (bx1, by1), (bx2, by2), (0,255,0), 2)
                            thumb = cv2.resize(crop_img, (320, 240))
                            audit_samples[c].append(thumb)

        if all(hp_counts[c] >= max_hp[c] for c in target_classes):
            break
            
    print(f"\nDONE! Final HPs: {hp_counts}. Generated {crops_generated} multi-scale crops.")
    print(f"Found {class_confusion} Class Confusion examples (IoU>0.5 but wrong class).")
    
    all_thumbs = audit_samples[0] + audit_samples[2] + audit_samples[4]
    cols = 5
    rows = math.ceil(len(all_thumbs) / cols)
    sheet_rows = []
    for r in range(rows):
        row_thumbs = all_thumbs[r * cols:(r + 1) * cols]
        if len(row_thumbs) < cols:
            row_thumbs += [np.ones((240, 320, 3), dtype="uint8") * 255] * (cols - len(row_thumbs))
        sheet_rows.append(cv2.hconcat(row_thumbs))
    if sheet_rows:
        sheet = cv2.vconcat(sheet_rows)
        cv2.imwrite(r"E:\GITHUB\a sih 2026\v4_hard_positive_audit.png", sheet)
        print("Audit sheet saved to E:\\GITHUB\\a sih 2026\\v4_hard_positive_audit.png")

if __name__ == "__main__":
    main()
