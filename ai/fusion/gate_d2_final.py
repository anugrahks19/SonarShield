import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from collections import defaultdict
import joblib

def load_ground_truth(val_labels_dir):
    gt_boxes = {}
    for label_file in Path(val_labels_dir).glob("*.txt"):
        image_id = label_file.stem + ".jpg" 
        boxes = []
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    boxes.append([float(p) for p in parts[:5]])
        gt_boxes[image_id] = boxes
    return gt_boxes

def compute_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0

def denormalize_box(norm_box, img_w=640, img_h=640):
    _, x, y, w, h = norm_box
    x1 = (x - w / 2) * img_w
    y1 = (y - h / 2) * img_h
    x2 = (x + w / 2) * img_w
    y2 = (y + h / 2) * img_h
    return [x1, y1, x2, y2]

def evaluate_metrics(y_true, y_probs, y_pred, name=""):
    if len(y_true) == 0:
        return
        
    pr_auc = average_precision_score(y_true, y_probs) if len(np.unique(y_true)) > 1 else np.nan
    roc_auc = roc_auc_score(y_true, y_probs) if len(np.unique(y_true)) > 1 else np.nan
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    
    print(f"\n--- {name} Metrics ---")
    print(f"PR-AUC:    {pr_auc:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"Recall:    {rec:.4f}  (TP: {tp} / {tp+fn})")
    print(f"Precision: {prec:.4f}  (TP: {tp} / {tp+fp})")
    print(f"F1 Score:  {f1:.4f}")
    print(f"FP Count:  {fp}")
    
    return {"pr_auc": pr_auc, "roc_auc": roc_auc, "recall": rec, "precision": prec, "f1": f1, "fp": fp, "tp": tp, "fn": fn}

def run_gate_d2_final():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    
    if not os.path.exists(results_file):
        print(f"Waiting for {results_file} to be generated...")
        return
        
    with open(results_file, 'r') as f:
        data = json.load(f)
        
    gt_boxes = load_ground_truth(val_labels_dir)
    
    # 1. Label candidates
    features = [
        "confidence", "local_contrast", "mean_intensity", "std_intensity", 
        "width_px", "height_px", "bbox_area_px", "aspect_ratio",
        "shadow_candidate_presence", "area_ratio", "mean_intensity_ratio", "adjacency",
        "boundary_strength", 
        "near_image_edge", "near_nadir", "dropout", "extreme_saturation", "very_low_dynamic_range"
    ]
    
    X_dict = defaultdict(list)
    y = []
    groups = []
    classes = []
    
    IOU_THRESH = 0.50 
    
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
                if iou >= IOU_THRESH:
                    is_tp = True
                    break
                    
        y.append(1 if is_tp else 0)
        groups.append(img_id)
        classes.append(cls_id)
        
        # Extract features
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
    
    total_tp = sum(y)
    total_fp = len(y) - total_tp
    print(f"Total labeled candidates across ALL validation images: {len(y)} (TP: {total_tp}, FP: {total_fp})")
    
    unique_classes, counts = np.unique(classes[y==1], return_counts=True)
    print("\nTP coverage per class:")
    for c, cnt in zip(unique_classes, counts):
        print(f"Class {c}: {cnt} True Positives")
        
    # 2. Create Splits (Grouped by image_id)
    # Dev: 60%, Calib: 20%, Test: 20%
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    
    X_dev, y_dev, groups_dev = X[dev_idx], y[dev_idx], groups[dev_idx]
    X_temp, y_temp, groups_temp = X[temp_idx], y[temp_idx], groups[temp_idx]
    
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    calib_idx_rel, test_idx_rel = next(gss2.split(X_temp, y_temp, groups=groups_temp))
    
    X_calib, y_calib = X_temp[calib_idx_rel], y_temp[calib_idx_rel]
    X_test, y_test, classes_test = X_temp[test_idx_rel], y_temp[test_idx_rel], classes[temp_idx][test_idx_rel]
    
    print(f"\nSplits (grouped by image_id):")
    print(f"DEV:   {len(y_dev)} candidates (TP: {sum(y_dev)})")
    print(f"CALIB: {len(y_calib)} candidates (TP: {sum(y_calib)})")
    print(f"TEST:  {len(y_test)} candidates (TP: {sum(y_test)})")
    
    # 3. Train Final Fusion Model on DEV
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42))
    ])
    pipeline.fit(X_dev, y_dev)
    
    # 4. Select Threshold on CALIB
    calib_probs = pipeline.predict_proba(X_calib)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_calib, calib_probs)
    idx = np.where(recalls >= 0.90)[0][-1] if len(np.where(recalls >= 0.90)[0]) > 0 else 0
    target_thresh = thresholds[idx] if idx < len(thresholds) else thresholds[-1]
    
    print(f"\nSelected Operating Threshold on CALIB for ~90% recall: {target_thresh:.4f}")
    
    # 5. Evaluate ONCE on Untouched TEST Set
    test_probs = pipeline.predict_proba(X_test)[:, 1]
    test_pred = (test_probs >= target_thresh).astype(int)
    
    evaluate_metrics(y_test, test_probs, test_pred, name="UNTOUCHED FINAL TEST SET (FUSION)")
    
    # Evaluate AI_ONLY on Test for comparison (confidence is feature index 0)
    # We must find the AI threshold on CALIB to be fair.
    ai_calib = X_calib[:, 0]
    precisions_ai, recalls_ai, thresholds_ai = precision_recall_curve(y_calib, ai_calib)
    idx_ai = np.where(recalls_ai >= 0.90)[0][-1] if len(np.where(recalls_ai >= 0.90)[0]) > 0 else 0
    target_thresh_ai = thresholds_ai[idx_ai] if idx_ai < len(thresholds_ai) else thresholds_ai[-1]
    
    ai_test = X_test[:, 0]
    ai_test_pred = (ai_test >= target_thresh_ai).astype(int)
    evaluate_metrics(y_test, ai_test, ai_test_pred, name="UNTOUCHED FINAL TEST SET (AI ONLY)")
    
    # 6. Per-class metrics on TEST Set (FUSION)
    print("\n--- FUSION Per-Class Metrics on Untouched Test Set ---")
    unique_classes_test = np.unique(classes_test)
    for c in unique_classes_test:
        mask = (classes_test == c)
        y_c = y_test[mask]
        y_pred_c = test_pred[mask]
        
        if len(y_c) == 0:
            continue
            
        tn_c, fp_c, fn_c, tp_c = confusion_matrix(y_c, y_pred_c, labels=[0, 1]).ravel()
        rec_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
        prec_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
        
        print(f"Class {c:2d}: TP={tp_c}/{tp_c+fn_c} ({rec_c:.2f}), FP={fp_c}, Prec={prec_c:.2f}")

    # 7. Freeze the model
    os.makedirs(r"E:\GITHUB\a sih 2026\ai\fusion\weights", exist_ok=True)
    model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    joblib.dump({
        "pipeline": pipeline,
        "threshold": target_thresh,
        "features": features
    }, model_path)
    print(f"\nFrozen fusion model saved to {model_path}")

if __name__ == "__main__":
    run_gate_d2_final()
