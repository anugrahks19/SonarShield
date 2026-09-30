import os
import shutil
import cv2
import json
import torch
from pathlib import Path
from ultralytics import YOLO
import matplotlib.pyplot as plt
from tqdm import tqdm
from preprocessing.pipeline import preprocess_sonar_image

class PreprocessingGateA:
    def __init__(self):
        self.model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
        self.val_clean_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images"
        self.val_clean_lbl_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\labels"
        self.bg_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images"
        
        self.modes = {
            "SOURCE_STATE_UNKNOWN": {"normalize": False, "denoise_method": "none", "use_clahe": False},
            "NORMALIZED": {"normalize": True, "denoise_method": "none", "use_clahe": False},
            "NORMALIZED_DENOISE": {"normalize": True, "denoise_method": "bilateral", "use_clahe": False},
            "NORMALIZED_CLAHE": {"normalize": True, "denoise_method": "none", "use_clahe": True},
            "NORMALIZED_DENOISE_CLAHE": {"normalize": True, "denoise_method": "bilateral", "use_clahe": True}
        }
        self.results = {}

    def prepare_dataset(self, mode_name, settings):
        print(f"\n--- Preparing Dataset for Mode: {mode_name} ---")
        dataset_path = Path(f"E:/GITHUB/a sih 2026/datasets/gate_a_{mode_name}")
        img_dir = dataset_path / "images" / "val"
        lbl_dir = dataset_path / "labels" / "val"
        
        yaml_path = dataset_path / f"dataset_{mode_name}.yaml"
        if dataset_path.exists() and yaml_path.exists():
            print(f"Dataset for {mode_name} already exists. Skipping preparation.")
            return yaml_path
            
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        
        # Copy labels
        for lbl_file in os.listdir(self.val_clean_lbl_dir):
            shutil.copy(os.path.join(self.val_clean_lbl_dir, lbl_file), lbl_dir / lbl_file)
            
        # Process and save images
        images = os.listdir(self.val_clean_img_dir)
        for img_file in tqdm(images, desc="Processing Images"):
            img_path = os.path.join(self.val_clean_img_dir, img_file)
            processed_img = preprocess_sonar_image(img_path, **settings)
            cv2.imwrite(str(img_dir / img_file), processed_img)
            
        # Create yaml
        yaml_content = f"""
path: {dataset_path.absolute()}
train: images/val
val: images/val
test: images/val

names:
  0: crab_pot
  1: submarine_pipeline
  2: shipwreck
  3: ghost_net
  4: mine_cylinder
"""
        with open(yaml_path, "w") as f:
            f.write(yaml_content)
            
        return yaml_path
        
    def evaluate_map(self, yaml_path, mode_name):
        print(f"\n--- Evaluating mAP for {mode_name} ---")
        model = YOLO(self.model_path)
        # Force conf=0.001 for standardized metric evaluation
        results = model.val(data=str(yaml_path), imgsz=640, split="val", conf=0.001, iou=0.7)
        
        ap50_dict = {int(c): float(ap) for c, ap in zip(results.box.ap_class_index, results.box.ap50)}
        
        return {
            "mAP50": float(results.box.map50),
            "mAP50-95": float(results.box.map),
            "precision": float(results.box.mp),
            "recall": float(results.box.mr),
            "crab_AP50": ap50_dict.get(0, 0.0),
            "pipeline_AP50": ap50_dict.get(1, 0.0),
            "shipwreck_AP50": ap50_dict.get(2, 0.0),
            "ghost_net_AP50": ap50_dict.get(3, 0.0),
            "mine_AP50": ap50_dict.get(4, 0.0)
        }

    def evaluate_fp(self, mode_name, settings):
        print(f"\n--- Evaluating False Positives for {mode_name} ---")
        model = YOLO(self.model_path)
        bg_images = [os.path.join(self.bg_img_dir, f) for f in os.listdir(self.bg_img_dir) if f.endswith(('.jpg', '.png'))]
        
        total_fps = 0
        fps_by_class = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        
        for img_path in tqdm(bg_images, desc="Running FP Benchmark"):
            processed_img = preprocess_sonar_image(img_path, **settings)
            # Use conf=0.25 to explicitly match the established baseline in evaluate_fp.py
            results = model(processed_img, imgsz=640, conf=0.25, verbose=False)[0]
            for box in results.boxes:
                cls = int(box.cls[0].cpu().numpy())
                fps_by_class[cls] += 1
                total_fps += 1
                
        return {
            "Total_FP": total_fps,
            "Crab_FP": fps_by_class[0],
            "Pipeline_FP": fps_by_class[1],
            "Shipwreck_FP": fps_by_class[2],
            "Ghost_Net_FP": fps_by_class[3],
            "Mine_FP": fps_by_class[4]
        }

    def run(self):
        for mode, settings in self.modes.items():
            yaml_path = self.prepare_dataset(mode, settings)
            map_metrics = self.evaluate_map(yaml_path, mode)
            fp_metrics = self.evaluate_fp(mode, settings)
            
            self.results[mode] = {**map_metrics, **fp_metrics}
            
        with open(r"E:\GITHUB\a sih 2026\preprocessing_results.json", "w") as f:
            json.dump(self.results, f, indent=4)
            
        print("Gate A execution completed. Results saved to preprocessing_results.json.")

if __name__ == "__main__":
    gate = PreprocessingGateA()
    gate.run()
