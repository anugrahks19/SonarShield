import os
from pathlib import Path
from ultralytics import YOLO

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector
import cv2
import torch
import numpy as np

def run_fp():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    bg_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images"
    bg_images = [os.path.join(bg_img_dir, f) for f in os.listdir(bg_img_dir) if f.endswith(('.jpg', '.png'))]
    
    print("Running Gate B FP Benchmark at conf=0.25")
    
    modes = ["GLOBAL", "TILED", "HYBRID"]
    
    detector = TiledDetector(model_path, conf=0.25, iou=0.7)
    
    results = {}
    
    for mode in modes:
        total_fp = 0
        for img_path in bg_images:
            image = cv2.imread(img_path)
            if mode == "GLOBAL":
                preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
            elif mode == "TILED":
                preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
            elif mode == "HYBRID":
                preds = detector.predict(image, trigger_conf=0.15, pure_tiled=False)
                
            if len(preds) > 0:
                total_fp += len(preds)
                
        results[mode] = total_fp
        print(f"{mode} Total FP: {total_fp}")

if __name__ == "__main__":
    run_fp()
