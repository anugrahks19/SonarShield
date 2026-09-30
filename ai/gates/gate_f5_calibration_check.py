import os
import json
import numpy as np
import joblib
from collections import defaultdict
import sys
from sklearn.model_selection import GroupShuffleSplit
from sklearn.calibration import calibration_curve

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box

def run_f5_calibration():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    
    with open(results_file, 'r') as f: data = json.load(f)
    gt_boxes = load_ground_truth(val_labels_dir)
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    model_data = joblib.load(fusion_model_path)
    pipeline = model_data["pipeline"]
    features = model_data["features"]
    
    X_dict = defaultdict(list)
    y, groups, classes = [], [], []
    
    for item in data:
        ev = item['evidence']
        img_id = item['image_id']
        bbox = ev['bbox']
        cls_id = ev['class']
        
        is_tp = False
        if img_id in gt_boxes:
            for gtb in gt_boxes[img_id]:
                if compute_iou(bbox, denormalize_box(gtb)) >= 0.50:
                    is_tp = True
                    break
                    
        y.append(1 if is_tp else 0)
        groups.append(img_id)
        classes.append(cls_id)
        
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
    y, groups, classes = np.array(y), np.array(groups), np.array(classes)
    
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    calib_idx_local, test_idx_local = next(gss2.split(X[temp_idx], y[temp_idx], groups=groups[temp_idx]))
    
    calib_idx = temp_idx[calib_idx_local]
    test_idx = temp_idx[test_idx_local]
    
    def get_scores_and_labels(idx_array):
        y_true = []
        y_prob = []
        c_labels = []
        for i in idx_array:
            x_vec = X[i].reshape(1, -1)
            fusion_score = pipeline.predict_proba(x_vec)[0, 1]
            y_true.append(y[i])
            y_prob.append(fusion_score)
            c_labels.append(classes[i])
        return np.array(y_true), np.array(y_prob), np.array(c_labels)
        
    calib_y, calib_prob, calib_cls = get_scores_and_labels(calib_idx)
    test_y, test_prob, test_cls = get_scores_and_labels(test_idx)
    
    class_map = {0: "Crab Pot", 1: "Wreck", 2: "Mine", 3: "Pipeline", 4: "Ghost Net"}
    calibrated_classes = [0, 1, 2] # Only calibrating Crab Pot, Wreck, Mine
    
    reliability_mapping = {}
    MIN_BIN_SIZE = 10
    
    print("\n--- GATE F5.1: FITTING RELIABILITY MAP ON CALIB ---")
    
    def fit_calibration(probs, labels):
        # 10 uniform bins
        bins = np.linspace(0, 1.0, 11)
        indices = np.digitize(probs, bins) - 1
        
        merged_bins = []
        current_bin = {"count": 0, "success": 0, "sum_prob": 0.0, "start": 0.0}
        
        for i in range(10):
            mask = (indices == i) | (indices == 10 if i == 9 else np.zeros_like(indices, dtype=bool))
            count = np.sum(mask)
            success = np.sum(labels[mask])
            sum_prob = np.sum(probs[mask])
            
            current_bin["count"] += count
            current_bin["success"] += success
            current_bin["sum_prob"] += sum_prob
            
            if current_bin["count"] >= MIN_BIN_SIZE or i == 9:
                if current_bin["count"] > 0:
                    merged_bins.append({
                        "range": [current_bin["start"], bins[i+1]],
                        "count": int(current_bin["count"]),
                        "estimated_tp_rate": float(current_bin["success"] / current_bin["count"]),
                        "mean_score": float(current_bin["sum_prob"] / current_bin["count"])
                    })
                else:
                    merged_bins.append({
                        "range": [current_bin["start"], bins[i+1]],
                        "count": 0,
                        "estimated_tp_rate": 0.0,
                        "mean_score": 0.0
                    })
                current_bin = {"count": 0, "success": 0, "sum_prob": 0.0, "start": bins[i+1]}
                
        # Assign presentation policy directly from calibrated TP rate
        for b in merged_bins:
            rate = b["estimated_tp_rate"]
            if rate >= 0.85:
                b["reliability_band"] = "HIGH_RELIABILITY"
                b["uncertainty_level"] = "LOW_UNCERTAINTY"
            elif rate >= 0.30:
                b["reliability_band"] = "MEDIUM_RELIABILITY"
                b["uncertainty_level"] = "MEDIUM_UNCERTAINTY"
            else:
                b["reliability_band"] = "LOW_RELIABILITY"
                b["uncertainty_level"] = "HIGH_UNCERTAINTY"
                
        return merged_bins
        
    for cls_id in calibrated_classes:
        c_name = class_map[cls_id]
        mask = (calib_cls == cls_id)
        if np.sum(mask) > 0:
            mapping = fit_calibration(calib_prob[mask], calib_y[mask])
            reliability_mapping[c_name] = mapping
            print(f"Class: {c_name} (N={np.sum(mask)})")
            for m in mapping:
                print(f"  Score [{m['range'][0]:.1f}-{m['range'][1]:.1f}] -> TP Rate: {m['estimated_tp_rate']:.3f} | {m['reliability_band']}")
        
    os.makedirs(r"E:\GITHUB\a sih 2026\ai\reliability\weights", exist_ok=True)
    with open(r"E:\GITHUB\a sih 2026\ai\reliability\weights\reliability_mapping.json", 'w') as f:
        json.dump(reliability_mapping, f, indent=4)
        
    print("\n--- GATE F5.2: EVALUATING ECE ON TEST ---")
    
    def evaluate_test_ece(probs, labels, c_name):
        mapping = reliability_mapping.get(c_name, [])
        if not mapping: return
        
        ece = 0.0
        for m in mapping:
            r_start, r_end = m['range']
            mask = (probs >= r_start) & ((probs < r_end) | (probs <= r_end if r_end == 1.0 else np.zeros_like(probs, dtype=bool)))
            n = np.sum(mask)
            if n > 0:
                test_precision = np.sum(labels[mask]) / n
                predicted_precision = m['estimated_tp_rate']
                ece += (n / len(probs)) * abs(test_precision - predicted_precision)
        return ece
        
    for cls_id in calibrated_classes:
        c_name = class_map[cls_id]
        mask = (test_cls == cls_id)
        if np.sum(mask) > 0:
            ece = evaluate_test_ece(test_prob[mask], test_y[mask], c_name)
            print(f"Class: {c_name} | ECE on TEST: {ece:.4f}")
            
    # Uncalibrated classes
    for cls_id in [3, 4]:
        reliability_mapping[class_map[cls_id]] = [{
            "range": [0.0, 1.0],
            "count": 0,
            "estimated_tp_rate": 0.0,
            "mean_score": 0.0,
            "reliability_band": "UNCALIBRATED",
            "uncertainty_level": "UNKNOWN"
        }]
        
    with open(r"E:\GITHUB\a sih 2026\ai\reliability\weights\reliability_mapping.json", 'w') as f:
        json.dump(reliability_mapping, f, indent=4)

if __name__ == "__main__":
    run_f5_calibration()
