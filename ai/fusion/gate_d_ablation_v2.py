import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from collections import defaultdict

def load_ground_truth(val_labels_dir):
    """Loads YOLO format annotations."""
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

def run_gate_d_ablation_v2():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_dev_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    
    with open(results_file, 'r') as f:
        data = json.load(f)
        
    gt_boxes = load_ground_truth(val_labels_dir)
    
    # Feature configurations
    feature_sets = {
        "AI_ONLY": ["confidence"],
        "AI_SEABED": ["confidence", "local_contrast", "mean_intensity", "std_intensity"],
        "AI_GEOMETRY": ["confidence", "width_px", "height_px", "bbox_area_px", "aspect_ratio"],
        "AI_SHADOW": ["confidence", "shadow_candidate_presence", "area_ratio", "mean_intensity_ratio", "adjacency"],
        "AI_BOUNDARY": ["confidence", "boundary_strength"],
        "AI_SEABED_GEOM_SHADOW": ["confidence", "local_contrast", "mean_intensity", "std_intensity", 
                                  "width_px", "height_px", "bbox_area_px", "aspect_ratio",
                                  "shadow_candidate_presence", "area_ratio", "mean_intensity_ratio", "adjacency"],
        "ALL_FEATURES": ["confidence", "local_contrast", "mean_intensity", "std_intensity", 
                         "width_px", "height_px", "bbox_area_px", "aspect_ratio",
                         "shadow_candidate_presence", "area_ratio", "mean_intensity_ratio", "adjacency",
                         "boundary_strength", 
                         "near_image_edge", "near_nadir", "dropout", "extreme_saturation", "very_low_dynamic_range"]
    }
    
    # 1. Label candidates
    X_dict = defaultdict(list)
    y = []
    groups = []
    classes = []
    
    IOU_THRESH = 0.50 # Primary positive label criterion
    
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
        
    y = np.array(y)
    groups = np.array(groups)
    classes = np.array(classes)
    
    total_tp = sum(y)
    total_fp = len(y) - total_tp
    print(f"Total labeled candidates: {len(y)} (TP: {total_tp}, FP: {total_fp})")
    
    # 2. Run Ablation with StratifiedGroupKFold and OOF Predictions
    print("\n--- Gate D Leakage-Safe Evidence Fusion Ablation ---")
    
    results_table = []
    
    for set_name, feature_names in feature_sets.items():
        X = np.column_stack([X_dict[f] for f in feature_names])
        
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42))
        ])
        
        oof_probs = np.zeros(len(y))
        
        for train_idx, test_idx in cv.split(X, y, groups=groups):
            X_train, y_train = X[train_idx], y[train_idx]
            X_test = X[test_idx]
            
            pipeline.fit(X_train, y_train)
            oof_probs[test_idx] = pipeline.predict_proba(X_test)[:, 1]
            
        pr_auc = average_precision_score(y, oof_probs)
        roc_auc = roc_auc_score(y, oof_probs)
        
        # Determine operating threshold globally on OOF predictions to achieve ~90% recall
        precisions, recalls, thresholds = precision_recall_curve(y, oof_probs)
        idx = np.where(recalls >= 0.90)[0][-1] if len(np.where(recalls >= 0.90)[0]) > 0 else 0
        target_thresh = thresholds[idx] if idx < len(thresholds) else thresholds[-1]
        
        y_pred = (oof_probs >= target_thresh).astype(int)
        
        tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        results_table.append({
            "Feature Set": set_name,
            "PR-AUC": f"{pr_auc:.4f}",
            "ROC-AUC": f"{roc_auc:.4f}",
            "Recall": f"{rec:.4f}",
            "Precision": f"{prec:.4f}",
            "FP": fp,
            "TP retained": tp
        })
        
        if set_name == "ALL_FEATURES":
            best_oof_probs = oof_probs
            best_thresh = target_thresh
            best_pred = y_pred

    df = pd.DataFrame(results_table)
    print("\n" + df.to_string(index=False))
    
    # 3. Class-Level Analysis on ALL_FEATURES
    print(f"\n--- Class-Level Analysis (ALL_FEATURES at thresh={best_thresh:.3f}) ---")
    unique_classes = np.unique(classes)
    for c in unique_classes:
        mask = (classes == c)
        y_c = y[mask]
        y_pred_c = best_pred[mask]
        
        if len(y_c) == 0:
            continue
            
        tn_c, fp_c, fn_c, tp_c = confusion_matrix(y_c, y_pred_c, labels=[0, 1]).ravel()
        rec_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0
        prec_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0
        
        print(f"Class {c:2d}: TP retained={tp_c}/{tp_c+fn_c} ({rec_c:.2f}), FP={fp_c}/{tn_c+fp_c}")

if __name__ == "__main__":
    run_gate_d_ablation_v2()
