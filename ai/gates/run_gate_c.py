import os
import sys
import cv2
import json
import random
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector
from evidence.evidence_extractor import extract_all_evidence

def run_gate_c():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    val_images_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\images\val"
    bg_images_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images"
    
    # We want ~100 diverse detections. 
    # Let's sample 50 images from val and 50 images from bg.
    val_images = list(Path(val_images_dir).glob("*.jpg")) + list(Path(val_images_dir).glob("*.png"))
    bg_images = list(Path(bg_images_dir).glob("*.jpg")) + list(Path(bg_images_dir).glob("*.png"))
    
    random.seed(42)
    sample_images = random.sample(val_images, min(50, len(val_images))) + random.sample(bg_images, min(50, len(bg_images)))
    
    detector = TiledDetector(model_path, conf=0.05, iou=0.7) # low conf to capture weak detections
    
    results = []
    
    print(f"Extracting evidence for {len(sample_images)} images...")
    
    for idx, img_path in enumerate(sample_images):
        img_path = str(img_path)
        image = cv2.imread(img_path)
        if image is None:
            continue
            
        # 1. Run GLOBAL
        global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
        for p in global_preds:
            p['source'] = 'GLOBAL'
            
        # 2. Run TILED to find recoveries (weak targets or FPs)
        tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
        for p in tiled_preds:
            p['source'] = 'TILED'
            
        # 3. Combine unique predictions (simplified NMS just based on very high IOU or center distance)
        # For evidence extraction, we just keep all, tagging them.
        all_candidates = global_preds
        
        # Add tiled preds that are far from global preds (misses recovered by tiled)
        for tp in tiled_preds:
            tx1, ty1, tx2, ty2 = tp['bbox']
            tcx = (tx1 + tx2) / 2
            tcy = (y1 + y2) / 2 if 'y1' in locals() else (ty1 + ty2) / 2
            
            is_new = True
            for gp in global_preds:
                gx1, gy1, gx2, gy2 = gp['bbox']
                gcx = (gx1 + gx2) / 2
                gcy = (gy1 + gy2) / 2
                dist = ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5
                if dist < 50: # Roughly same object
                    is_new = False
                    break
            
            if is_new:
                all_candidates.append(tp)
                
        # 4. Extract Evidence
        import hashlib
        config_hash = hashlib.md5("gate_c_v1_conf=0.05_iou=0.7".encode()).hexdigest()[:8]
        image_id = os.path.basename(img_path)
        
        for cand_idx, cand in enumerate(all_candidates):
            evidence = extract_all_evidence(image, cand)
            
            # Store metadata
            results.append({
                "extractor_version": "gate_c_v1",
                "config_hash": config_hash,
                "image_id": image_id,
                "candidate_id": f"{image_id}_cand_{cand_idx}",
                "image_path": img_path,
                "evidence": evidence
            })
            
    # Save results
    out_dir = r"E:\GITHUB\a sih 2026\ai\reference"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "gate_c_results.json")
    
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"Extraction complete! Saved {len(results)} evidence vectors to {out_file}")

if __name__ == "__main__":
    run_gate_c()
