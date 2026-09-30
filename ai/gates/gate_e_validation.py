import os
import json
import numpy as np
import joblib
from collections import defaultdict
import sys
import cv2
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box
from reliability.decision_engine import DecisionEngine
from gates.gate_e_visual_audit import draw_transparent_box

def run_gate_e_validation():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    val_images_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\images\val"
    
    with open(results_file, 'r') as f:
        data = json.load(f)
        
    gt_boxes = load_ground_truth(val_labels_dir)
    
    # Load fusion model for feature parsing
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    model_data = joblib.load(fusion_model_path)
    pipeline = model_data["pipeline"]
    features = model_data["features"]
    
    X_dict = defaultdict(list)
    y = []
    classes = []
    groups = []
    ev_list = []
    
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
        ev_list.append(item)
        
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
    
    # Split identically to D-2
    from sklearn.model_selection import GroupShuffleSplit
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    
    X_temp, y_temp, groups_temp = X[temp_idx], y[temp_idx], groups[temp_idx]
    
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    calib_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=groups_temp))
    
    # Get actual indices for test set
    actual_test_idx = temp_idx[test_idx]
    
    engine = DecisionEngine()
    
    test_decisions = []
    test_y = []
    test_classes = []
    test_items = []
    
    ai_only_threshold = 0.2085 # the 90% recall threshold from calib AI_ONLY in gate D2
    ai_decisions = []
    
    for idx in actual_test_idx:
        x_vec = X[idx].reshape(1, -1)
        x_std = pipeline.named_steps['scaler'].transform(x_vec)
        fusion_score = pipeline.predict_proba(x_vec)[0, 1]
        
        ev_dict = ev_list[idx]['evidence']
        payload = engine.evaluate_candidate(ev_dict, x_std, fusion_score)
        
        test_decisions.append(payload['decision'])
        test_y.append(y[idx])
        test_classes.append(classes[idx])
        test_items.append(ev_list[idx])
        
        # AI ONLY logic mapping to decision
        conf = ev_dict['confidence']
        # Simplified AI ONLY mapping: REJECT < threshold, REVIEW/CONFIRM > threshold based on arbitrary high conf
        if conf < ai_only_threshold:
            ai_decisions.append("REJECT")
        elif conf < 0.8:
            ai_decisions.append("REVIEW")
        else:
            ai_decisions.append("CONFIRM")
            
    test_decisions = np.array(test_decisions)
    test_y = np.array(test_y)
    test_classes = np.array(test_classes)
    ai_decisions = np.array(ai_decisions)
    
    print("--- GATE E VALIDATION (TEST SET) ---")
    
    print("\nDecision Distribution (FUSION):")
    for d in ["REJECT", "REVIEW", "CONFIRM", "UNKNOWN"]:
        mask = (test_decisions == d)
        print(f"{d:8s}: {np.sum(mask)} candidates (TP={np.sum(test_y[mask]==1)}, FP={np.sum(test_y[mask]==0)})")
        
    print("\nDecision Distribution (AI-ONLY):")
    for d in ["REJECT", "REVIEW", "CONFIRM"]:
        mask = (ai_decisions == d)
        print(f"{d:8s}: {np.sum(mask)} candidates (TP={np.sum(test_y[mask]==1)}, FP={np.sum(test_y[mask]==0)})")
        
    print("\n--- Key Metrics ---")
    
    total_tp = np.sum(test_y == 1)
    conf_mask = (test_decisions == "CONFIRM")
    conf_tp = np.sum(test_y[conf_mask] == 1)
    conf_fp = np.sum(test_y[conf_mask] == 0)
    
    precision = conf_tp / (conf_tp + conf_fp) if (conf_tp + conf_fp) > 0 else 0
    coverage = conf_tp / total_tp if total_tp > 0 else 0
    
    print(f"CONFIRM precision: {precision:.4f} ({conf_tp}/{conf_tp+conf_fp})")
    print(f"CONFIRM coverage:  {coverage:.4f} ({conf_tp}/{total_tp})")
    print(f"REVIEW count:      {np.sum(test_decisions == 'REVIEW')}")
    print(f"REJECT count:      {np.sum(test_decisions == 'REJECT')}")
    print(f"UNKNOWN count:     {np.sum(test_decisions == 'UNKNOWN')}")
    
    known_tp_to_unknown = np.sum((test_y == 1) & (test_decisions == "UNKNOWN") & (np.isin(test_classes, [0, 1, 2])))
    print(f"Known candidates routed UNKNOWN: {known_tp_to_unknown}")
    
    uncalibrated_forced_review = np.sum((np.isin(test_classes, [3, 4])) & (test_decisions == "REVIEW"))
    print(f"Uncalibrated candidates forced REVIEW: {uncalibrated_forced_review}")
    
    print("\nPer-class TP routing:")
    class_map = {0: "Crab Pot", 1: "Wreck", 2: "Mine", 3: "Pipeline", 4: "Ghost Net"}
    for cls_id in range(5):
        mask = (test_y == 1) & (test_classes == cls_id)
        if np.sum(mask) == 0:
            print(f"{class_map[cls_id]}: 0 TP in test set")
            continue
        print(f"{class_map[cls_id]} ({np.sum(mask)} TPs):")
        for d in ["REJECT", "REVIEW", "CONFIRM", "UNKNOWN"]:
            d_mask = mask & (test_decisions == d)
            print(f"  {d}: {np.sum(d_mask)}")
            
    # Generate visual examples
    out_dir = r"E:\GITHUB\a sih 2026\ai\reference\gate_e_validation_examples"
    os.makedirs(out_dir, exist_ok=True)
    
    # We want: known TP->UNKNOWN, known FP->UNKNOWN, known TP->CONFIRM, known FP->CONFIRM, etc.
    # We'll grab first instance of each
    targets = {
        "known_TP_to_UNKNOWN": (1, "UNKNOWN"),
        "known_FP_to_UNKNOWN": (0, "UNKNOWN"),
        "known_TP_to_CONFIRM": (1, "CONFIRM"),
        "known_FP_to_CONFIRM": (0, "CONFIRM"),
        "known_TP_to_REVIEW":  (1, "REVIEW"),
        "known_FP_to_REVIEW":  (0, "REVIEW"),
        "known_TP_to_REJECT":  (1, "REJECT")
    }
    
    rendered = set()
    
    for i, (dec, yt, cls_id) in enumerate(zip(test_decisions, test_y, test_classes)):
        if cls_id in [3, 4]: continue
        
        for t_name, (t_y, t_dec) in targets.items():
            if t_name not in rendered and yt == t_y and dec == t_dec:
                # render it
                item = test_items[i]
                img_path = os.path.join(val_images_dir, item['image_id'] + ".jpg")
                if os.path.exists(img_path):
                    img = cv2.imread(img_path)
                    x1, y1, x2, y2 = item['evidence']['bbox']
                    
                    if dec == "CONFIRM": color = (0, 255, 0)
                    elif dec == "REVIEW": color = (0, 165, 255)
                    elif dec == "REJECT": color = (0, 0, 255)
                    else: color = (255, 0, 255)
                    
                    img = draw_transparent_box(img, x1, y1, x2, y2, color, alpha=0.3)
                    cv2.putText(img, f"{dec} (TP={yt})", (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    out_path = os.path.join(out_dir, f"{t_name}.jpg")
                    cv2.imwrite(out_path, img)
                    rendered.add(t_name)
                    
    print(f"\nSaved audit images to {out_dir}")

if __name__ == "__main__":
    run_gate_e_validation()
