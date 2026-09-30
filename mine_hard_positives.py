import os
import cv2
import yaml
import shutil
import random
from pathlib import Path
from ultralytics import YOLO

def box_iou(box1, box2):
    # box: [x, y, w, h] normalized
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
    V4_HP_IMG.mkdir(parents=True, exist_ok=True)
    V4_HP_LBL.mkdir(parents=True, exist_ok=True)
    
    model = YOLO(r"E:\GITHUB\a sih 2026\models\v3\detector_v3-2\weights\best.pt")
    
    target_classes = {0, 2, 4} # crab, shipwreck, mine
    max_hp = {0: 500, 2: 300, 4: 200}
    hp_counts = {0: 0, 2: 0, 4: 0}
    
    scales = [1.3, 1.8, 2.5]
    
    images = list(TRAIN_IMG.glob("*"))
    random.seed(42)
    random.shuffle(images)
    
    crops_generated = 0
    
    for idx, img_path in enumerate(images):
        lbl_path = TRAIN_LBL / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            continue
            
        with open(lbl_path, "r") as f:
            gt_lines = [l.strip().split() for l in f.readlines() if l.strip()]
            
        if not gt_lines: continue
        
        # Check if any GT is in our target classes AND we still need it
        has_target = False
        for gt in gt_lines:
            c = int(gt[0])
            if c in target_classes and hp_counts[c] < max_hp[c]:
                has_target = True
                break
                
        if not has_target:
            continue
            
        # Run inference
        res = model(str(img_path), conf=0.25, verbose=False)
        pred_boxes = res[0].boxes
        
        preds = []
        for box in pred_boxes:
            c = int(box.cls.item())
            x, y, w, h = box.xywhn[0].tolist()
            preds.append((c, [x, y, w, h]))
            
        img = None
        
        for gt_idx, gt in enumerate(gt_lines):
            c = int(gt[0])
            if c not in target_classes:
                continue
            if hp_counts[c] >= max_hp[c]:
                continue
                
            gx, gy, gw, gh = map(float, gt[1:5])
            gt_box = [gx, gy, gw, gh]
            
            # Find best IOU among predictions of SAME class
            best_iou = 0.0
            for pc, pbox in preds:
                if pc == c:
                    iou = box_iou(gt_box, pbox)
                    if iou > best_iou:
                        best_iou = iou
                        
            # If model missed it or poor localization
            if best_iou < 0.5:
                hp_counts[c] += 1
                
                if img is None:
                    img = cv2.imread(str(img_path))
                    if img is None: break
                    ih, iw = img.shape[:2]
                
                # Generate multiscale crops
                for scale in scales:
                    crop_w = int(gw * iw * scale)
                    crop_h = int(gh * ih * scale)
                    
                    # Ensure minimum crop size (e.g. 100x100) to give context
                    crop_w = max(crop_w, 100)
                    crop_h = max(crop_h, 100)
                    
                    # Center of GT
                    cx = int(gx * iw)
                    cy = int(gy * ih)
                    
                    x1 = max(0, cx - crop_w // 2)
                    y1 = max(0, cy - crop_h // 2)
                    x2 = min(iw, cx + crop_w // 2)
                    y2 = min(ih, cy + crop_h // 2)
                    
                    crop_img = img[y1:y2, x1:x2]
                    if crop_img.shape[0] < 10 or crop_img.shape[1] < 10:
                        continue
                        
                    # Calculate new GT box in crop coordinates
                    c_iw = x2 - x1
                    c_ih = y2 - y1
                    
                    # Target GT coordinates relative to crop
                    new_cx = cx - x1
                    new_cy = cy - y1
                    new_gw = gw * iw
                    new_gh = gh * ih
                    
                    # Normalize
                    n_cx = new_cx / c_iw
                    n_cy = new_cy / c_ih
                    n_w = new_gw / c_iw
                    n_h = new_gh / c_ih
                    
                    # Clamp
                    n_cx = min(max(n_cx, 0), 1)
                    n_cy = min(max(n_cy, 0), 1)
                    n_w = min(n_w, 1)
                    n_h = min(n_h, 1)
                    
                    out_stem = f"{img_path.stem}_hp_{gt_idx}_s{int(scale*10)}"
                    cv2.imwrite(str(V4_HP_IMG / f"{out_stem}.jpg"), crop_img)
                    
                    with open(V4_HP_LBL / f"{out_stem}.txt", "w") as f:
                        f.write(f"{c} {n_cx:.6f} {n_cy:.6f} {n_w:.6f} {n_h:.6f}\n")
                        
                    crops_generated += 1

        if (idx + 1) % 500 == 0:
            print(f"Processed {idx+1} images. HPs Found: {hp_counts}. Generated {crops_generated} crops.")
            
        if all(hp_counts[c] >= max_hp[c] for c in target_classes):
            print("Reached target capacities for all hard positive classes!")
            break
            
    print(f"\nDONE! Final HPs: {hp_counts}. Generated {crops_generated} multi-scale crops.")

if __name__ == "__main__":
    main()
