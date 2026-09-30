import os
import json
import numpy as np
import joblib
from collections import defaultdict
import sys
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import precision_recall_curve

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box

def inspect_curve():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    with open(results_file, 'r') as f: data = json.load(f)
    gt_boxes = load_ground_truth(val_labels_dir)
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
        is_tp = False
        if img_id in gt_boxes:
            for gtb in gt_boxes[img_id]:
                if compute_iou(bbox, denormalize_box(gtb)) >= 0.50:
                    is_tp = True
                    break
        y.append(1 if is_tp else 0)
        classes.append(ev['class'])
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
    y, groups, classes = np.array(y), np.array(groups), np.array(classes)
    
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    calib_idx, test_idx = next(gss2.split(X[temp_idx], y[temp_idx], groups=groups[temp_idx]))
    actual_calib_idx = temp_idx[calib_idx]
    
    X_calib = X[actual_calib_idx]
    y_calib = y[actual_calib_idx]
    classes_calib = classes[actual_calib_idx]
    
    probs = pipeline.predict_proba(X_calib)[:, 1]
    
    mask = (classes_calib == 1) # shipwreck
    prec, rec, thresh = precision_recall_curve(y_calib[mask], probs[mask])
    for p, r, t in zip(prec, rec, thresh):
        if p >= 0.8:
            print(f"Thresh: {t:.4f}, Prec: {p:.4f}, Rec: {r:.4f}")
            
if __name__ == "__main__":
    inspect_curve()
