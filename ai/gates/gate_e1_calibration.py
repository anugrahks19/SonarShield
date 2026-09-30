import os
import json
import numpy as np
import joblib
from collections import defaultdict
from sklearn.ensemble import IsolationForest
import sys
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import precision_recall_curve

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box

def run_gate_e1_calibration():
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
        
        for f in features:
            if f == "confidence": val = ev["confidence"]
            elif f in ["local_contrast", "mean_intensity", "std_intensity"]: val = ev["seabed"][f]
            elif f in ["width_px", "height_px", "bbox_area_px", "aspect_ratio"]: val = ev["object"][f]
            elif f in ["shadow_candidate_presence", "area_ratio", "mean_intensity_ratio", "adjacency"]: val = ev["shadow"][f]
            elif f == "boundary_strength": val = ev["quality"][f]
            elif f in ev["quality"]["artifact_flags"]: val = 1 if ev["quality"]["artifact_flags"][f] else 0
            else: val = 0
            X_dict[f].append(val)
            
    X = np.column_stack([X_dict[f] for f in features])
    y = np.array(y)
    groups = np.array(groups)
    classes = np.array(classes)
    
    # EXACT D-2 SPLITS
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    
    X_temp, y_temp, groups_temp, classes_temp = X[temp_idx], y[temp_idx], groups[temp_idx], classes[temp_idx]
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    calib_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=groups_temp))
    
    # DEV, CALIB, TEST sets
    X_dev, y_dev, classes_dev = X[dev_idx], y[dev_idx], classes[dev_idx]
    actual_calib_idx = temp_idx[calib_idx]
    X_calib, y_calib, classes_calib = X[actual_calib_idx], y[actual_calib_idx], classes[actual_calib_idx]
    actual_test_idx = temp_idx[test_idx]
    X_test, y_test, classes_test = X[actual_test_idx], y[actual_test_idx], classes[actual_test_idx]
    
    print(f"Data Shapes -> DEV: {len(X_dev)}, CALIB: {len(X_calib)}, TEST: {len(X_test)}")
    
    probs_calib = pipeline.predict_proba(X_calib)[:, 1]
    
    # Class-specific thresholds on CALIB
    policy = {"classes": {}}
    
    class_map = {0: "crab_pot", 1: "shipwreck", 2: "mine_cylinder"}
    
    for cls_id in [0, 1, 2]:
        mask_calib = (classes_calib == cls_id)
        if np.sum(mask_calib & (y_calib == 1)) == 0:
            print(f"WARNING: Class {class_map[cls_id]} has NO True Positives in CALIB!")
            continue
            
        y_c = y_calib[mask_calib]
        p_c = probs_calib[mask_calib]
        
        prec, rec, thresh = precision_recall_curve(y_c, p_c)
        
        # Target ~90% recall for REVIEW (or lowest possible if 90% is unreachable)
        valid_rec_idx = np.where(rec >= 0.90)[0]
        if len(valid_rec_idx) > 0:
            idx_90_rec = valid_rec_idx[-1]
            if idx_90_rec >= len(thresh): idx_90_rec = len(thresh) - 1
            review_thresh = thresh[idx_90_rec]
        else:
            review_thresh = 0.0 # fallback
            
        # Target ~85% precision for CONFIRM (or highest precision if 85% is unreachable)
        valid_prec_idx = np.where(prec >= 0.85)[0]
        if len(valid_prec_idx) > 0:
            idx_85_prec = valid_prec_idx[0]
            if idx_85_prec >= len(thresh): idx_85_prec = len(thresh) - 1
            confirm_thresh = thresh[idx_85_prec]
        else:
            # if 85% precision is unreachable, we take the max precision available, or 0.99
            confirm_thresh = thresh[-1]
            
        policy["classes"][str(cls_id)] = {
            "review_threshold": float(review_thresh),
            "confirm_threshold": float(confirm_thresh)
        }
        print(f"Class {class_map[cls_id]}: REVIEW >= {review_thresh:.4f}, CONFIRM >= {confirm_thresh:.4f}")
        
    # Isolation Forest on DEV TPs
    tp_mask_dev = (y_dev == 1) & (np.isin(classes_dev, [0, 1, 2]))
    X_tp_dev = X_dev[tp_mask_dev]
    
    # Tune IF operating point: contamination = 0.02 to retain ~98% of valid known TPs.
    iso_forest = IsolationForest(n_estimators=100, contamination=0.02, random_state=42)
    X_tp_dev_scaled = pipeline.named_steps['scaler'].transform(X_tp_dev)
    iso_forest.fit(X_tp_dev_scaled)
    
    os.makedirs(r"E:\GITHUB\a sih 2026\ai\reliability\weights", exist_ok=True)
    with open(r"E:\GITHUB\a sih 2026\ai\reliability\weights\score_policy.json", 'w') as f:
        json.dump(policy, f, indent=4)
        
    joblib.dump(iso_forest, r"E:\GITHUB\a sih 2026\ai\reliability\weights\unknown_detector.pkl")
    print("\nGate E.1 Calibration saved successfully.")

if __name__ == "__main__":
    run_gate_e1_calibration()
