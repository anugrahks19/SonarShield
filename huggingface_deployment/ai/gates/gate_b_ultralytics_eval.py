import torch
from ultralytics.models.yolo.detect.val import DetectionValidator
from ultralytics import YOLO
import cv2
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector

def run_ultralytics_eval(mode="GLOBAL"):
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    data_path = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\dataset_SOURCE_STATE_UNKNOWN.yaml"
    
    detector = TiledDetector(model_path, conf=0.001, iou=0.7)
    
    # Initialize validator
    validator = DetectionValidator(args=dict(
        model=model_path,
        data=data_path,
        imgsz=640,
        conf=0.001,
        iou=0.7,
        split='val',
        plots=False,
        save_json=False
    ))
    
    # We must manually setup the validator
    validator.data = validator.get_dataset(validator.args.data)
    validator.dataloader = validator.get_dataloader(validator.data.get("val"), validator.args.batch)
    validator.device = torch.device('cuda')
    validator.init_metrics(YOLO(model_path).model)
    
    print(f"Evaluating {mode} using Ultralytics primary logic...")
    
    for batch_i, batch in enumerate(validator.dataloader):
        batch = validator.preprocess(batch)
        
        preds_list = []
        for i, im_file in enumerate(batch["im_file"]):
            img = cv2.imread(im_file)
            ori_h, ori_w = img.shape[:2]
            
            if mode == "GLOBAL":
                preds = detector.predict(img, trigger_conf=-1.0, pure_tiled=False)
            elif mode == "TILED":
                preds = detector.predict(img, trigger_conf=2.0, pure_tiled=True)
            elif mode == "HYBRID":
                preds = detector.predict(img, trigger_conf=0.15, pure_tiled=False)
                
            # preds are in [x1, y1, x2, y2] original image coordinates.
            # DetectionValidator expects predictions from the model to be in the padded 640x640 format.
            # But wait! update_metrics has this:
            # predn = self._prepare_pred(pred) -> just copies it
            # Then self._process_batch(predn, pbatch) -> computes IoU
            # But where does it scale from 640x640 to original?
            # update_metrics expects `pred` to be [N, 6] tensor (xyxy, conf, cls) in the LETTERBOXED coordinates!
            
            # Let's scale our original coords to letterboxed coords using batch["ratio_pad"]
            # batch["ratio_pad"][i] is (ratio, pad) where pad is (pad_w, pad_h)
            ratio, (pad_w, pad_h) = batch["ratio_pad"][i]
            
            boxes_640 = []
            for p in preds:
                x1, y1, x2, y2 = p["bbox"]
                # Scale and pad
                x1 = x1 * ratio[0] + pad_w
                x2 = x2 * ratio[0] + pad_w
                y1 = y1 * ratio[1] + pad_h
                y2 = y2 * ratio[1] + pad_h
                boxes_640.append([x1, y1, x2, y2, p["detector_confidence"], p["class"]])
                
            if len(boxes_640) > 0:
                pred_tensor = torch.tensor(boxes_640, device=validator.device)
            else:
                pred_tensor = torch.zeros((0, 6), device=validator.device)
                
            preds_list.append(pred_tensor)
            
        validator.update_metrics(preds_list, batch)
        
    stats = validator.get_stats()
    validator.print_results()
    
    # stats contains (mp, mr, map50, map, etc)
    return stats

if __name__ == "__main__":
    run_ultralytics_eval("GLOBAL")
