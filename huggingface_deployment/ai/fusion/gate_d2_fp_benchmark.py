import os
import sys
import cv2
import json
import numpy as np
from pathlib import Path
import joblib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector
from evidence.evidence_extractor import extract_all_evidence

def run_gate_d2_fp_benchmark():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    bg_images_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images"
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    
    if not os.path.exists(fusion_model_path):
        print(f"Fusion model not found at {fusion_model_path}")
        return
        
    model_data = joblib.load(fusion_model_path)
    pipeline = model_data["pipeline"]
    threshold = model_data["threshold"]
    features = model_data["features"]
    
    detector = TiledDetector(model_path, conf=0.05, iou=0.7)
    
    bg_images = list(Path(bg_images_dir).glob("*.jpg")) + list(Path(bg_images_dir).glob("*.png"))
    
    print(f"Running Final FP Benchmark on {len(bg_images)} locked background images...")
    
    total_candidates = 0
    final_fps = 0
    
    for idx, img_path in enumerate(bg_images):
        img_path = str(img_path)
        image = cv2.imread(img_path)
        if image is None:
            continue
            
        global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
        tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
        
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
                
        total_candidates += len(all_candidates)
        
        # Extract evidence and run fusion
        for cand in all_candidates:
            ev = extract_all_evidence(image, cand)
            
            # Build feature vector
            x_dict = {}
            x_dict["confidence"] = ev["confidence"]
            x_dict["local_contrast"] = ev["seabed"]["local_contrast"]
            x_dict["mean_intensity"] = ev["seabed"]["mean_intensity"]
            x_dict["std_intensity"] = ev["seabed"]["std_intensity"]
            x_dict["width_px"] = ev["object"]["width_px"]
            x_dict["height_px"] = ev["object"]["height_px"]
            x_dict["bbox_area_px"] = ev["object"]["bbox_area_px"]
            x_dict["aspect_ratio"] = ev["object"]["aspect_ratio"]
            x_dict["shadow_candidate_presence"] = ev["shadow"]["shadow_candidate_presence"]
            x_dict["area_ratio"] = ev["shadow"]["area_ratio"]
            x_dict["mean_intensity_ratio"] = ev["shadow"]["mean_intensity_ratio"]
            x_dict["adjacency"] = ev["shadow"]["adjacency"]
            x_dict["boundary_strength"] = ev["quality"]["boundary_strength"]
            
            flags = ev["quality"]["artifact_flags"]
            x_dict["near_image_edge"] = 1 if flags.get("near_image_edge") else 0
            x_dict["near_nadir"] = 1 if flags.get("near_nadir") else 0
            x_dict["dropout"] = 1 if flags.get("dropout") else 0
            x_dict["extreme_saturation"] = 1 if flags.get("extreme_saturation") else 0
            x_dict["very_low_dynamic_range"] = 1 if flags.get("very_low_dynamic_range") else 0
            
            x_vec = np.array([[x_dict[f] for f in features]])
            
            prob = pipeline.predict_proba(x_vec)[0, 1]
            if prob >= threshold:
                final_fps += 1
                
        if idx > 0 and idx % 20 == 0:
            print(f"Processed {idx}/{len(bg_images)} images. Found {final_fps} FPs so far.")
            
    print("\n--- Gate D-2 FP Benchmark Complete ---")
    print(f"Total raw candidates generated: {total_candidates}")
    print(f"Total False Positives retained after fusion thresholding: {final_fps}")

if __name__ == "__main__":
    run_gate_d2_fp_benchmark()
