import os
import cv2
import json
import torch
from pathlib import Path
from tqdm import tqdm
from ultralytics import YOLO
from torchmetrics.detection.mean_ap import MeanAveragePrecision

# Add parent dir to path to import tiled_detector
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector

class GateBEvaluator:
    def __init__(self):
        self.model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
        self.val_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images"
        self.val_lbl_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\labels"
        self.bg_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images"
        
        self.modes = ["GLOBAL", "TILED", "HYBRID"]
        self.results = {}

    def _parse_labels(self, txt_path, img_w, img_h):
        boxes = []
        labels = []
        if os.path.exists(txt_path):
            with open(txt_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        cls_id = int(parts[0])
                        # YOLO format: x_center, y_center, w, h
                        x_c, y_c, w, h = map(float, parts[1:])
                        x1 = (x_c - w/2) * img_w
                        y1 = (y_c - h/2) * img_h
                        x2 = (x_c + w/2) * img_w
                        y2 = (y_c + h/2) * img_h
                        boxes.append([x1, y1, x2, y2])
                        labels.append(cls_id)
        if len(boxes) == 0:
            return torch.empty((0, 4)), torch.empty((0,), dtype=torch.int64)
        return torch.tensor(boxes), torch.tensor(labels, dtype=torch.int64)

    def evaluate_map(self, mode):
        print(f"\n--- Evaluating mAP for {mode} ---")
        
        metric_50 = MeanAveragePrecision(iou_type="bbox", iou_thresholds=[0.5], class_metrics=True)
        metric_all = MeanAveragePrecision(iou_type="bbox", class_metrics=True)
        
        # Detector for mAP logic (conf=0.001)
        detector = TiledDetector(self.model_path, conf=0.001, iou=0.7)
        
        images = [f for f in os.listdir(self.val_img_dir) if f.endswith(('.jpg', '.png'))]
        
        for img_file in tqdm(images, desc=f"Evaluating {mode}"):
            img_path = os.path.join(self.val_img_dir, img_file)
            lbl_path = os.path.join(self.val_lbl_dir, img_file.rsplit('.', 1)[0] + '.txt')
            
            image = cv2.imread(img_path)
            img_h, img_w = image.shape[:2]
            
            gt_boxes, gt_labels = self._parse_labels(lbl_path, img_w, img_h)
            
            # Predict
            if mode == "GLOBAL":
                preds = detector.predict(image, trigger_conf=-1.0) # Never tile
            elif mode == "TILED":
                preds = detector.predict(image, trigger_conf=2.0) # Always tile
            elif mode == "HYBRID":
                preds = detector.predict(image, trigger_conf=0.15) # Hybrid logic
                
            pred_boxes = []
            pred_scores = []
            pred_labels = []
            
            for p in preds:
                pred_boxes.append(p["bbox"])
                pred_scores.append(p["detector_confidence"])
                pred_labels.append(p["class"])
                
            if len(pred_boxes) == 0:
                pred_boxes = torch.empty((0, 4))
                pred_scores = torch.empty((0,))
                pred_labels = torch.empty((0,), dtype=torch.int64)
            else:
                pred_boxes = torch.tensor(pred_boxes)
                pred_scores = torch.tensor(pred_scores)
                pred_labels = torch.tensor(pred_labels, dtype=torch.int64)
                
            target = [dict(boxes=gt_boxes, labels=gt_labels)]
            preds_dict = [dict(boxes=pred_boxes, scores=pred_scores, labels=pred_labels)]
            
            metric_50.update(preds_dict, target)
            metric_all.update(preds_dict, target)
            
        res_50 = metric_50.compute()
        res_all = metric_all.compute()
        
        # Extract per-class AP50. Note: class_metrics returns a list matching unique labels, 
        # but torchmetrics orders them. If a class is missing, we must be careful.
        # MeanAveragePrecision returns map_per_class as a tensor of all 5 classes if seen.
        
        map_per_class_50 = res_50['map_per_class'].tolist() if 'map_per_class' in res_50 else [0,0,0,0,0]
        # Pad if some classes are completely missing from val set (rare)
        while len(map_per_class_50) < 5:
            map_per_class_50.append(0.0)
            
        return {
            "mAP50": float(res_50['map_50']),
            "mAP50-95": float(res_all['map']),
            # Torchmetrics returns mar_100 instead of recall, which is roughly equivalent for our case
            "recall": float(res_all['mar_100']), 
            "crab_AP50": float(map_per_class_50[0]),
            "pipeline_AP50": float(map_per_class_50[1]),
            "shipwreck_AP50": float(map_per_class_50[2]),
            "ghost_net_AP50": float(map_per_class_50[3]),
            "mine_AP50": float(map_per_class_50[4])
        }

    def evaluate_fp(self, mode):
        print(f"\n--- Evaluating False Positives for {mode} ---")
        
        # FP uses conf=0.25 to match baseline
        detector = TiledDetector(self.model_path, conf=0.25, iou=0.7)
        
        bg_images = [os.path.join(self.bg_img_dir, f) for f in os.listdir(self.bg_img_dir) if f.endswith(('.jpg', '.png'))]
        total_fps = 0
        fps_by_class = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        
        for img_path in tqdm(bg_images, desc="Running FP Benchmark"):
            image = cv2.imread(img_path)
            
            if mode == "GLOBAL":
                preds = detector.predict(image, trigger_conf=-1.0)
            elif mode == "TILED":
                preds = detector.predict(image, trigger_conf=2.0)
            elif mode == "HYBRID":
                preds = detector.predict(image, trigger_conf=0.15)
                
            for p in preds:
                cls = p["class"]
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
        for mode in self.modes:
            map_metrics = self.evaluate_map(mode)
            fp_metrics = self.evaluate_fp(mode)
            
            self.results[mode] = {**map_metrics, **fp_metrics}
            
        out_path = r"E:\GITHUB\a sih 2026\ai\reference\gate_b_results.json"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(self.results, f, indent=4)
            
        print("Gate B execution completed.")

if __name__ == "__main__":
    gate = GateBEvaluator()
    gate.run()
