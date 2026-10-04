import cv2
import numpy as np
import torch
from ultralytics import YOLO
from torchvision.ops import batched_nms

class TiledDetector:
    def __init__(self, model_path, conf=0.15, iou=0.7, device=None):
        """
        SAHI-style coarse-to-fine detector.
        """
        self.model = YOLO(model_path)
        self.conf = conf
        self.iou = iou
        self.device = device
        
    def predict(self, image, trigger_conf=0.20, tile_size=384, overlap=0.25, pure_tiled=False):
        """
        Global inference with optional tiled fallback.
        """
        candidates = []
        max_conf = 0.0
        
        if not pure_tiled:
            # 1. Global Inference
            global_results = self.model(image, conf=self.conf, iou=self.iou, imgsz=640, verbose=False, device=self.device)[0]
            
            for box in global_results.boxes:
                b = box.xyxy[0].cpu().numpy()
                c = float(box.conf[0].cpu().numpy())
                cls = int(box.cls[0].cpu().numpy())
                
                candidates.append({
                    "class": cls,
                    "bbox": [float(b[0]), float(b[1]), float(b[2]), float(b[3])],
                    "detector_confidence": c,
                    "source": "global"
                })
                if c > max_conf:
                    max_conf = c
                    
        # 2. Check if Tiling Triggered (Hybrid logic)
        # Tile if pure_tiled is forced OR (trigger_conf >= 0 AND (no candidates OR best candidate is weak))
        if pure_tiled or (trigger_conf >= 0 and (len(candidates) == 0 or max_conf < trigger_conf)):
            h, w = image.shape[:2]
            stride = int(tile_size * (1 - overlap))
            
            tiled_candidates = []
            
            for y in range(0, h, stride):
                for x in range(0, w, stride):
                    y1, y2 = y, min(h, y + tile_size)
                    x1, x2 = x, min(w, x + tile_size)
                    
                    # Pad if smaller than tile_size
                    tile = np.zeros((tile_size, tile_size, 3), dtype=np.uint8)
                    tile_h, tile_w = y2 - y1, x2 - x1
                    tile[0:tile_h, 0:tile_w] = image[y1:y2, x1:x2]
                    
                    # Inference on tile (resized to 640 internally by YOLO)
                    tile_results = self.model(tile, conf=self.conf, iou=self.iou, imgsz=640, verbose=False, device=self.device)[0]
                    
                    for box in tile_results.boxes:
                        b = box.xyxy[0].cpu().numpy()
                        c = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        
                        # Remap to global coordinates
                        global_x1 = x1 + b[0]
                        global_y1 = y1 + b[1]
                        global_x2 = x1 + b[2]
                        global_y2 = y1 + b[3]
                        
                        # Keep only valid boxes
                        if global_x2 <= w and global_y2 <= h:
                            tiled_candidates.append({
                                "class": cls,
                                "bbox": [float(global_x1), float(global_y1), float(global_x2), float(global_y2)],
                                "detector_confidence": c,
                                "source": f"tile_{x}_{y}"
                            })
            
            candidates.extend(tiled_candidates)
            candidates = self.apply_class_aware_nms(candidates)
            
        return candidates

    def apply_class_aware_nms(self, candidates):
        if not candidates:
            return []
            
        boxes = torch.tensor([c["bbox"] for c in candidates])
        scores = torch.tensor([c["detector_confidence"] for c in candidates])
        class_ids = torch.tensor([c["class"] for c in candidates])
        
        keep_indices = batched_nms(boxes, scores, class_ids, iou_threshold=self.iou)
        
        return [candidates[idx] for idx in keep_indices]
