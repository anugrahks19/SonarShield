import os
import json
import numpy as np
from pathlib import Path
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve, confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

def load_ground_truth(val_labels_dir):
    """
    Loads YOLO format annotations. Returns dict mapping image_id to list of bboxes [cls, x, y, w, h] (normalized).
    """
    gt_boxes = {}
    for label_file in Path(val_labels_dir).glob("*.txt"):
        image_id = label_file.stem + ".jpg" # assuming jpg
        boxes = []
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    boxes.append([float(p) for p in parts[:5]])
        gt_boxes[image_id] = boxes
    return gt_boxes

def compute_iou(box1, box2):
    # box1: [x1, y1, x2, y2]
    # box2: [x1, y1, x2, y2]
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0

def denormalize_box(norm_box, img_w=640, img_h=640): # assuming 640 for simple matching
    _, x, y, w, h = norm_box
    x1 = (x - w / 2) * img_w
    y1 = (y - h / 2) * img_h
    x2 = (x + w / 2) * img_w
    y2 = (y + h / 2) * img_h
    return [x1, y1, x2, y2]

def run_gate_d_ablation():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_results.json"
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
                         # boolean flags mapped to 0/1
                         "near_image_edge", "near_nadir", "dropout", "extreme_saturation", "very_low_dynamic_range"]
    }
    
    # 1. Label candidates and build master feature matrix
    X_dict = {f: [] for f in feature_sets["ALL_FEATURES"]}
    y = []
    
    for item in data:
        ev = item['evidence']
        img_id = item.get('image_id', os.path.basename(item.get('image_path', '')))
        bbox = ev['bbox']
        
        # Labeling logic
        is_tp = False
        if img_id in gt_boxes:
            for gtb in gt_boxes[img_id]:
                gt_bbox = denormalize_box(gtb)
                iou = compute_iou(bbox, gt_bbox)
                if iou > 0.3: # Using 0.3 for relaxed matching to avoid penalizing valid detections slightly off
                    is_tp = True
                    break
        y.append(1 if is_tp else 0)
        
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
        
        # Flags
        flags = ev["quality"]["artifact_flags"]
        X_dict["near_image_edge"].append(1 if flags.get("near_image_edge") else 0)
        X_dict["near_nadir"].append(1 if flags.get("near_nadir") else 0)
        X_dict["dropout"].append(1 if flags.get("dropout") else 0)
        X_dict["extreme_saturation"].append(1 if flags.get("extreme_saturation") else 0)
        X_dict["very_low_dynamic_range"].append(1 if flags.get("very_low_dynamic_range") else 0)
        
    y = np.array(y)
    print(f"Total labeled candidates: {len(y)} (TP: {sum(y)}, FP: {len(y) - sum(y)})")
    
    # 2. Run Ablation
    print("\n--- Gate D Evidence Fusion Ablation ---")
    print(f"{'Feature Set':<25} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'FP at 90% Recall':<18}")
    print("-" * 65)
    
    for set_name, feature_names in feature_sets.items():
        X = np.column_stack([X_dict[f] for f in feature_names])
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Simple Linear Model (Logistic Regression) to test linear separability of features
        clf = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
        
        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        y_probs = cross_val_predict(clf, X_scaled, y, cv=cv, method='predict_proba')[:, 1]
        
        # Metrics
        pr_auc = average_precision_score(y, y_probs)
        roc_auc = roc_auc_score(y, y_probs)
        
        # Find False Positives at 90% Recall
        precisions, recalls, thresholds = precision_recall_curve(y, y_probs)
        # Find index where recall is closest to 0.90, but >= 0.90
        idx = np.where(recalls >= 0.90)[0][-1] if len(np.where(recalls >= 0.90)[0]) > 0 else 0
        target_thresh = thresholds[idx] if idx < len(thresholds) else thresholds[-1]
        
        y_pred = (y_probs >= target_thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
        
        print(f"{set_name:<25} | {pr_auc:.4f}   | {roc_auc:.4f}   | {fp} (out of {tn+fp} true negatives)")

if __name__ == "__main__":
    run_gate_d_ablation()
