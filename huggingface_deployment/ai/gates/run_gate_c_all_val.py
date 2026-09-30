import os
import sys
import cv2
import json
import random
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector
from evidence.evidence_extractor import extract_all_evidence

def run_gate_c_all_val():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    # Process the entire validation set to ensure coverage of all classes
    val_images_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\images\val"
    
    sample_images = list(Path(val_images_dir).glob("*.jpg")) + list(Path(val_images_dir).glob("*.png"))
    
    detector = TiledDetector(model_path, conf=0.05, iou=0.7)
    
    results = []
    
    print(f"Extracting evidence for ALL {len(sample_images)} validation images...")
    
    import hashlib
    config_hash = hashlib.md5("gate_c_all_val_v1_conf=0.05_iou=0.7".encode()).hexdigest()[:8]
    
    for idx, img_path in enumerate(sample_images):
        img_path = str(img_path)
        image_id = os.path.basename(img_path)
        image = cv2.imread(img_path)
        if image is None:
            continue
            
        global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
        for p in global_preds:
            p['source'] = 'GLOBAL'
            
        tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
        for p in tiled_preds:
            p['source'] = 'TILED'
            
        all_candidates = global_preds
        
        for tp in tiled_preds:
            tx1, ty1, tx2, ty2 = tp['bbox']
            tcx = (tx1 + tx2) / 2
            tcy = (ty1 + ty2) / 2
            
            is_new = True
            for gp in global_preds:
                gx1, gy1, gx2, gy2 = gp['bbox']
                gcx = (gx1 + gx2) / 2
                gcy = (gy1 + gy2) / 2
                dist = ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5
                if dist < 50:
                    is_new = False
                    break
            
            if is_new:
                all_candidates.append(tp)
                
        for cand_idx, cand in enumerate(all_candidates):
            evidence = extract_all_evidence(image, cand)
            
            results.append({
                "extractor_version": "gate_c_v1",
                "config_hash": config_hash,
                "image_id": image_id,
                "candidate_id": f"{image_id}_cand_{cand_idx}",
                "image_path": img_path,
                "evidence": evidence
            })
            
    out_dir = r"E:\GITHUB\a sih 2026\ai\reference"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "gate_c_all_val_results.json")
    
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"Extraction complete! Saved {len(results)} evidence vectors to {out_file}")

if __name__ == "__main__":
    run_gate_c_all_val()
