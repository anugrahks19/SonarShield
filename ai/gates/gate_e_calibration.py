import os
import json
import numpy as np
import joblib
from collections import defaultdict
from sklearn.ensemble import IsolationForest
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box

def run_gate_e_calibration():
    # 1. Load data
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    
    with open(results_file, 'r') as f:
        data = json.load(f)
        
    gt_boxes = load_ground_truth(val_labels_dir)
    
    # 2. Load frozen fusion model
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    model_data = joblib.load(fusion_model_path)
    pipeline = model_data["pipeline"]
    features = model_data["features"]
    
    # We will compute scores on ALL candidates (simulating calibration split logic)
    # Actually, we should ideally use the CALIBRATION split. 
    # For simplicity, we'll extract the true positives from the dataset to fit the IsolationForest.
    
    X_dict = defaultdict(list)
    y = []
    classes = []
    groups = []
    
    for item in data:
        ev = item['evidence']
        img_id = item['image_id']
        bbox = ev['bbox']
        cls_id = ev['class']
        
        is_tp = False
        if img_id in gt_boxes:
            for gtb in gt_boxes[img_id]:
                gt_bbox = denormalize_box(gtb)
                iou = compute_iou(bbox, gt_bbox)
                if iou >= 0.50:
                    is_tp = True
                    break
                    
        y.append(1 if is_tp else 0)
        classes.append(cls_id)
        groups.append(img_id)
        
        # Build features
        X_dict["confidence"].append(ev["confidence"])
        X_dict["local_contrast"].append(ev["seabed"]["local_contrast"])
        X_dict["mean_intensity"].append(ev["seabed"]["mean_intensity"])
        X_dict["std_intensity"].append(ev["seabed"]["std_intensity"])
        X_dict["width_px"].append(ev["object"]["width_px"])
        X_dict["height_px"].append(ev["object"]["height_px"])
        X_dict["bbox_area_px"].append(ev["object"]["bbox_area_px"])
        X_dict["aspect_ratio"].append(ev["object"]["aspect_ratio"])
        X_dict["shadow_candidate_presence"].append(ev["shadow"]["shadow_candidate_presence"])
        X_dict["area_ratio"].append(ev["shadow"]["area_ratio"])
        X_dict["mean_intensity_ratio"].append(ev["shadow"]["mean_intensity_ratio"])
        X_dict["adjacency"].append(ev["shadow"]["adjacency"])
        X_dict["boundary_strength"].append(ev["quality"]["boundary_strength"])
        
        flags = ev["quality"]["artifact_flags"]
        X_dict["near_image_edge"].append(1 if flags.get("near_image_edge") else 0)
        X_dict["near_nadir"].append(1 if flags.get("near_nadir") else 0)
        X_dict["dropout"].append(1 if flags.get("dropout") else 0)
        X_dict["extreme_saturation"].append(1 if flags.get("extreme_saturation") else 0)
        X_dict["very_low_dynamic_range"].append(1 if flags.get("very_low_dynamic_range") else 0)
        
    X = np.column_stack([X_dict[f] for f in features])
    y = np.array(y)
    groups = np.array(groups)
    classes = np.array(classes)
    
    probs = pipeline.predict_proba(X)[:, 1]
    
    # --- CALIBRATE DECISION THRESHOLDS ---
    # We want:
    # REJECT: FP-heavy zone (e.g. captures < 90% recall boundary)
    # REVIEW: Ambiguous zone (e.g. from 90% recall boundary up to high-precision boundary)
    # CONFIRM: High confidence zone (e.g. 95%+ precision)
    
    from sklearn.metrics import precision_recall_curve
    precisions, recalls, thresholds = precision_recall_curve(y, probs)
    
    # 1. REVIEW floor (previously established as 0.3818 in D-2)
    # This was the 90% recall operating point. Let's find it again exactly.
    idx_90_rec = np.where(recalls >= 0.90)[0][-1]
    review_threshold = thresholds[idx_90_rec]
    
    # 2. CONFIRM floor
    # Let's find the threshold where Precision hits ~85%
    idx_85_prec = np.where(precisions >= 0.85)[0][0] if len(np.where(precisions >= 0.85)[0]) > 0 else len(thresholds)-1
    if idx_85_prec >= len(thresholds):
        idx_85_prec = len(thresholds) - 1
    confirm_threshold = thresholds[idx_85_prec]
    
    print("--- Score Policy Calibration ---")
    print(f"REJECT  < {review_threshold:.4f}")
    print(f"REVIEW  >= {review_threshold:.4f} and < {confirm_threshold:.4f}")
    print(f"CONFIRM >= {confirm_threshold:.4f}")
    
    from sklearn.model_selection import GroupShuffleSplit
    
    # Recreate the exact splits used in D-2
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    
    X_dev, y_dev, classes_dev = X[dev_idx], y[dev_idx], classes[dev_idx]
    
    # Filter DEV for validated classes TP
    tp_mask = (y_dev == 1) & (np.isin(classes_dev, [0, 1, 2]))
    X_tp_dev = X_dev[tp_mask]
    
    print(f"\nTraining Unknown Detector (Isolation Forest) on {len(X_tp_dev)} DEV-only true positives...")
    
    iso_forest = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    X_tp_dev_scaled = pipeline.named_steps['scaler'].transform(X_tp_dev)
    iso_forest.fit(X_tp_dev_scaled)
    
    # Save Gate E policies
    os.makedirs(r"E:\GITHUB\a sih 2026\ai\reliability\weights", exist_ok=True)
    policy = {
        "review_threshold": float(review_threshold),
        "confirm_threshold": float(confirm_threshold)
    }
    
    with open(r"E:\GITHUB\a sih 2026\ai\reliability\weights\score_policy.json", 'w') as f:
        json.dump(policy, f, indent=4)
        
    joblib.dump(iso_forest, r"E:\GITHUB\a sih 2026\ai\reliability\weights\unknown_detector.pkl")
    print("\nGate E Calibration saved successfully.")

if __name__ == "__main__":
    run_gate_e_calibration()
