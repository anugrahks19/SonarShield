import os
import cv2
import random
from pathlib import Path

# CONFIG
TRAIN_IMG_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\images")
TRAIN_LBL_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\labels")
OUT_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\v3_crab_crops")

OUT_IMG_DIR = OUT_DIR / "images"
OUT_LBL_DIR = OUT_DIR / "labels"
OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)
OUT_LBL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CLASS = 0  # crab_pot
TARGET_CROPS = 1000
MAX_CROPS_PER_IMG = 2
EXPAND_MIN = 1.5
EXPAND_MAX = 2.0

random.seed(42)

def generate_crops():
    # Find all images containing crab pots
    labels = list(TRAIN_LBL_DIR.glob("*.txt"))
    crab_images = []
    
    for lbl_path in labels:
        with open(lbl_path, "r") as f:
            lines = [l.strip().split() for l in f.readlines() if l.strip()]
        
        crab_boxes = [l for l in lines if int(l[0]) == TARGET_CLASS]
        if crab_boxes:
            crab_images.append((lbl_path.stem, lines, crab_boxes))
            
    print(f"Found {len(crab_images)} images with crab pots.")
    
    # Shuffle to ensure diversity
    random.shuffle(crab_images)
    
    total_crops = 0
    
    for stem, all_boxes, crab_boxes in crab_images:
        if total_crops >= TARGET_CROPS:
            break
            
        img_path = TRAIN_IMG_DIR / f"{stem}.jpg"
        if not img_path.exists():
            img_path = TRAIN_IMG_DIR / f"{stem}.png"
            if not img_path.exists():
                continue
                
        img = cv2.imread(str(img_path))
        if img is None:
            continue
            
        h, w = img.shape[:2]
        
        # Limit crops per image
        selected_crabs = random.sample(crab_boxes, min(len(crab_boxes), MAX_CROPS_PER_IMG))
        
        for idx, crab in enumerate(selected_crabs):
            if total_crops >= TARGET_CROPS:
                break
                
            _, xc, yc, bw, bh = map(float, crab)
            
            # Pixel coordinates
            px_xc, px_yc = xc * w, yc * h
            px_bw, px_bh = bw * w, bh * h
            
            # Expansion factor
            expand = random.uniform(EXPAND_MIN, EXPAND_MAX)
            crop_w = px_bw * expand
            crop_h = px_bh * expand
            
            # Ensure crop is at least 64x64 to avoid tiny resolution issues before resize
            crop_w = max(crop_w, 64)
            crop_h = max(crop_h, 64)
            
            # Crop bounds
            x1 = int(px_xc - crop_w / 2)
            y1 = int(px_yc - crop_h / 2)
            x2 = int(px_xc + crop_w / 2)
            y2 = int(px_yc + crop_h / 2)
            
            # Shift if out of bounds
            if x1 < 0:
                x2 -= x1
                x1 = 0
            if y1 < 0:
                y2 -= y1
                y1 = 0
            if x2 > w:
                x1 -= (x2 - w)
                x2 = w
            if y2 > h:
                y1 -= (y2 - h)
                y2 = h
                
            # Final bounds check
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            crop_img = img[y1:y2, x1:x2]
            actual_crop_w = x2 - x1
            actual_crop_h = y2 - y1
            
            # Resize to 640x640
            crop_img_resized = cv2.resize(crop_img, (640, 640))
            
            new_labels = []
            # Recalculate boxes for all objects that fall inside the crop
            for box in all_boxes:
                b_cls = box[0]
                b_xc, b_yc, b_w, b_h = map(float, box[1:])
                
                # Convert to absolute pixels
                abs_xc, abs_yc = b_xc * w, b_yc * h
                abs_w, abs_h = b_w * w, b_h * h
                
                # Check if center is inside crop
                if x1 <= abs_xc <= x2 and y1 <= abs_yc <= y2:
                    # New center relative to crop
                    new_xc = (abs_xc - x1) / actual_crop_w
                    new_yc = (abs_yc - y1) / actual_crop_h
                    # New width/height relative to crop
                    # Clip width/height to not exceed crop boundaries
                    new_w = min(abs_w, actual_crop_w) / actual_crop_w
                    new_h = min(abs_h, actual_crop_h) / actual_crop_h
                    
                    new_labels.append(f"{b_cls} {new_xc:.6f} {new_yc:.6f} {new_w:.6f} {new_h:.6f}")
                    
            if not new_labels:
                continue # Should theoretically always have at least the crab pot
                
            # Save
            out_name = f"{stem}_crop{idx}"
            cv2.imwrite(str(OUT_IMG_DIR / f"{out_name}.jpg"), crop_img_resized)
            with open(OUT_LBL_DIR / f"{out_name}.txt", "w") as lf:
                lf.write("\n".join(new_labels) + "\n")
                
            total_crops += 1

    print(f"Successfully generated {total_crops} crab-focused crop views.")

if __name__ == "__main__":
    generate_crops()
