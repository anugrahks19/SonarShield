import os
from pathlib import Path
from ultralytics import YOLO

BG_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images")
bg_images = list(BG_DIR.glob("*"))

models = {
    "V1": r"E:\GITHUB\a sih 2026\models\v1\detector_v1-2\weights\best.pt",
    "V2-HN": r"E:\GITHUB\a sih 2026\models\v2\detector_v2_hn-4\weights\best.pt",
    "V3": r"E:\GITHUB\a sih 2026\models\v3\detector_v3-2\weights\best.pt",
    "V4": r"E:\GITHUB\a sih 2026\models\v4\detector_v4-2\weights\best.pt",
    "V5": r"E:\GITHUB\a sih 2026\models\v5\detector_v5_m640\weights\best.pt",
    "V6": r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
}

print("Running FP Evaluation on 324 Independent Backgrounds...")
print("Using conf=0.25 for all models.\n")

for name, path in models.items():
    if not os.path.exists(path):
        print(f"Skipping {name}: Weights not found at {path}")
        continue
        
    model = YOLO(path)
    
    total_fp = 0
    images_with_fp = 0
    class_fp = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    
    for img in bg_images:
        res = model(str(img), conf=0.25, verbose=False)
        boxes = res[0].boxes
        if len(boxes) > 0:
            images_with_fp += 1
            total_fp += len(boxes)
            for cls in boxes.cls:
                class_fp[int(cls.item())] += 1
                
    print(f"--- {name} ---")
    print(f"Images tested: {len(bg_images)}")
    print(f"Images with >=1 FP: {images_with_fp}")
    print(f"Total FP detections: {total_fp}")
    print(f"FP/image: {total_fp / len(bg_images):.3f}")
    print(f"Crab-pot FP: {class_fp[0]}")
    print(f"Submarine Pipeline FP: {class_fp[1]}")
    print(f"Shipwreck FP: {class_fp[2]}")
    print(f"Ghost-net FP: {class_fp[3]}")
    print(f"Mine FP: {class_fp[4]}\n")
