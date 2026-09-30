import os
import cv2
import sys
import numpy as np
import joblib
from pathlib import Path
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from detection.tiled_detector import TiledDetector
from evidence.evidence_extractor import extract_all_evidence
from reliability.decision_engine import DecisionEngine
from reliability.reliability_report import generate_sonar_shield_report

def draw_transparent_box(img, x1, y1, x2, y2, color, alpha=0.3):
    overlay = img.copy()
    cv2.rectangle(overlay, (int(x1), int(y1)), (int(x2), int(y2)), color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
    return img

def run_gate_e_audit():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    val_images_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\images\val"
    
    # Load frozen fusion pipeline
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    model_data = joblib.load(fusion_model_path)
    pipeline = model_data["pipeline"]
    features = model_data["features"]
    
    decision_engine = DecisionEngine()
    detector = TiledDetector(model_path, conf=0.05, iou=0.7)
    
    images = list(Path(val_images_dir).glob("*.jpg"))
    random.seed(123)
    sample_images = random.sample(images, 5)
    
    out_dir = r"E:\GITHUB\a sih 2026\ai\reference\gate_e_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    for idx, img_path in enumerate(sample_images):
        img_path = str(img_path)
        image = cv2.imread(img_path)
        if image is None: continue
        
        display_img = image.copy()
        
        global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
        tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
        
        all_candidates = global_preds
        for tp in tiled_preds:
            tx1, ty1, tx2, ty2 = tp['bbox']
            tcx, tcy = (tx1 + tx2) / 2, (ty1 + ty2) / 2
            is_new = True
            for gp in global_preds:
                gx1, gy1, gx2, gy2 = gp['bbox']
                gcx, gcy = (gx1 + gx2) / 2, (gy1 + gy2) / 2
                if ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5 < 50:
                    is_new = False
                    break
            if is_new:
                all_candidates.append(tp)
                
        for cand in all_candidates:
            ev = extract_all_evidence(image, cand)
            
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
            
            # Predict fusion score
            fusion_score = pipeline.predict_proba(x_vec)[0, 1]
            
            # Standardized features for UNKNOWN detection
            x_std = pipeline.named_steps['scaler'].transform(x_vec)
            
            payload = decision_engine.evaluate_candidate(ev, x_std, fusion_score)
            decision = payload["decision"]
            
            report = generate_sonar_shield_report(payload)
            print(f"\n--- Candidate on {os.path.basename(img_path)} ---")
            print(report)
            
            x1, y1, x2, y2 = ev['bbox']
            if decision == "CONFIRM":
                color = (0, 255, 0)
            elif decision == "REVIEW":
                color = (0, 165, 255)
            elif decision == "REJECT":
                color = (0, 0, 255)
            else: # UNKNOWN
                color = (255, 0, 255)
                
            display_img = draw_transparent_box(display_img, x1, y1, x2, y2, color, alpha=0.3)
            
            cv2.putText(display_img, f"{decision} ({fusion_score:.2f})", (int(x1), int(y1)-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
        out_path = os.path.join(out_dir, f"audit_e_{idx}.jpg")
        cv2.imwrite(out_path, display_img)
        
    print(f"\nGate E Audit saved images to {out_dir}")

if __name__ == "__main__":
    run_gate_e_audit()
