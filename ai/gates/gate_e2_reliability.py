import os
import json
import numpy as np
import joblib
from collections import defaultdict
import sys
from sklearn.model_selection import GroupShuffleSplit
import scipy.stats as stats

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box
from reliability.decision_engine import DecisionEngine

def compute_ci(successes, total, conf=0.95):
    if total == 0: return (0.0, 0.0)
    p = successes / total
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    spread = z * np.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2))) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))

def run_gate_e2_reliability():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    
    with open(results_file, 'r') as f: data = json.load(f)
    gt_boxes = load_ground_truth(val_labels_dir)
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    model_data = joblib.load(fusion_model_path)
    pipeline = model_data["pipeline"]
    features = model_data["features"]
    
    X_dict = defaultdict(list)
    y, classes, groups, ev_list = [], [], [], []
    
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
        classes.append(cls_id)
        groups.append(img_id)
        ev_list.append(item)
        
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
    actual_test_idx = temp_idx[test_idx]
    
    engine = DecisionEngine()
    test_decisions, test_y, test_classes = [], [], []
    abl_ai_tp, abl_ai_fp = 0, 0
    abl_fus_tp, abl_fus_fp = 0, 0
    abl_fusif_tp, abl_fusif_fp = 0, 0
    
    for idx in actual_test_idx:
        x_vec = X[idx].reshape(1, -1)
        x_std = pipeline.named_steps['scaler'].transform(x_vec)
        fusion_score = pipeline.predict_proba(x_vec)[0, 1]
        ev_dict = ev_list[idx]['evidence']
        
        ai_conf = ev_dict['confidence']
        if ai_conf >= 0.2085:
            if y[idx] == 1: abl_ai_tp += 1
            else: abl_ai_fp += 1
            
        if fusion_score >= 0.3818:
            if y[idx] == 1: abl_fus_tp += 1
            else: abl_fus_fp += 1
            
        is_anom = engine.unknown_detector.check_unknown(x_std)
        if fusion_score >= 0.3818 and not is_anom:
            if y[idx] == 1: abl_fusif_tp += 1
            else: abl_fusif_fp += 1
            
        payload = engine.evaluate_candidate(ev_dict, x_std, fusion_score)
        test_decisions.append(payload['decision'])
        test_y.append(y[idx])
        test_classes.append(classes[idx])
        
    test_decisions, test_y, test_classes = np.array(test_decisions), np.array(test_y), np.array(test_classes)
    
    e2_surfaced_mask = np.isin(test_decisions, ["REVIEW", "CONFIRM", "UNKNOWN"])
    e2_tp = np.sum(test_y[e2_surfaced_mask] == 1)
    e2_fp = np.sum(test_y[e2_surfaced_mask] == 0)
    
    print("--- GATE E.2 ABLATION STUDY ---")
    print(f"AI-only      : TP Surfaced = {abl_ai_tp:3d}, FP Surfaced = {abl_ai_fp:3d}")
    print(f"Fusion       : TP Surfaced = {abl_fus_tp:3d}, FP Surfaced = {abl_fus_fp:3d}")
    print(f"Fusion + IF  : TP Surfaced = {abl_fusif_tp:3d}, FP Surfaced = {abl_fusif_fp:3d}")
    print(f"Final Gate E2: TP Surfaced = {e2_tp:3d}, FP Surfaced = {e2_fp:3d}")
    
    print("\n--- CLASS-WISE ROUTING MATRIX ---")
    class_map = {0: "Crab Pot", 1: "Wreck", 2: "Mine", 3: "Pipeline", 4: "Ghost Net"}
    header = f"{'Class':<12} | {'LOW_EVID':<8} | {'REVIEW':<8} | {'CONFIRM':<8} | {'UNKNOWN':<8}"
    print(header)
    print("-" * len(header))
    for cls_id in range(5):
        mask_cls = (test_classes == cls_id)
        if np.sum(mask_cls) == 0: continue
        low_ev = np.sum(mask_cls & (test_decisions == "LOW_EVIDENCE") & (test_y == 1))
        rev = np.sum(mask_cls & (test_decisions == "REVIEW") & (test_y == 1))
        conf = np.sum(mask_cls & (test_decisions == "CONFIRM") & (test_y == 1))
        unk = np.sum(mask_cls & (test_decisions == "UNKNOWN") & (test_y == 1))
        print(f"{class_map[cls_id]:<12} | {low_ev:<8} | {rev:<8} | {conf:<8} | {unk:<8} (TPs)")
        
    # Metrics
    total_candidates = len(test_y)
    total_tp = np.sum(test_y == 1)
    total_fp = np.sum(test_y == 0)
    
    # Surfaced
    surfaced_tp = np.sum((test_y == 1) & np.isin(test_decisions, ["REVIEW", "CONFIRM", "UNKNOWN"]))
    
    # Review
    review_mask = (test_decisions == "REVIEW")
    review_tp = np.sum(test_y[review_mask] == 1)
    review_total = np.sum(review_mask)
    
    # Confirm
    confirm_mask = (test_decisions == "CONFIRM")
    confirm_tp = np.sum(test_y[confirm_mask] == 1)
    confirm_total = np.sum(confirm_mask)
    confirm_precision = confirm_tp / confirm_total if confirm_total > 0 else 1.0
    
    # Unknown
    unknown_mask = (test_decisions == "UNKNOWN")
    unknown_fp = np.sum(test_y[unknown_mask] == 0)
    unknown_tp = np.sum(test_y[unknown_mask] == 1)
    
    # Low Ev
    low_ev_mask = (test_decisions == "LOW_EVIDENCE")
    
    print("\n--- OPERATIONAL EFFICIENCY METRICS ---")
    print(f"Total Candidates Evaluated: {total_candidates}")
    print(f"  LOW_EVIDENCE : {np.sum(low_ev_mask)/total_candidates*100:.1f}%")
    print(f"  REVIEW       : {review_total/total_candidates*100:.1f}%")
    print(f"  UNKNOWN      : {np.sum(unknown_mask)/total_candidates*100:.1f}%")
    print(f"  CONFIRM      : {confirm_total/total_candidates*100:.1f}%")
    
    print(f"\nTarget Surfacing Recall: {surfaced_tp/total_tp*100:.1f}% ({surfaced_tp}/{total_tp})")
    print(f"Review Precision       : {review_tp/review_total*100:.1f}% ({review_tp}/{review_total})")
    if confirm_total > 0:
        low, high = compute_ci(confirm_tp, confirm_total)
        print(f"CONFIRM Precision      : {confirm_precision*100:.1f}% 95% CI: [{low*100:.1f}%, {high*100:.1f}%]")
    else:
        print(f"CONFIRM Precision      : N/A (0 confirms)")
    print(f"UNKNOWN FP Capture     : {unknown_fp/total_fp*100:.1f}% ({unknown_fp}/{total_fp})")
    print(f"Candidate-Level Review Workload Relative to a 100% Manual-Inspection Baseline: {(review_total + np.sum(unknown_mask))/total_candidates*100:.1f}%")
    
    print("\n--- ISOLATION FOREST ---")
    print(f"Empirical TP retention (Test Set): {100 - (unknown_tp/total_tp)*100:.2f}% ({total_tp-unknown_tp}/{total_tp})")
    
    # Assertions
    print("\n--- AUTOMATED ACCEPTANCE TESTS ---")
    assert confirm_precision >= 0.85, f"FAIL: CONFIRM precision {confirm_precision*100:.1f}% < 85%"
    print("PASS: CONFIRM precision >= 85%")
    assert surfaced_tp / total_tp >= 0.85, f"FAIL: TP Surfaced {surfaced_tp/total_tp*100:.1f}% < 85%"
    print("PASS: TP Surfaced Recall >= 85%")
    assert unknown_tp <= 10, f"FAIL: UNKNOWN TP loss {unknown_tp} > 10"
    print("PASS: UNKNOWN TP loss acceptable")
    
    policy = engine.score_policy.policy
    manifest = {
        "gate": "E",
        "version": "1.2.0",
        "model_artifact": "gate_d_fusion_model.pkl",
        "decision_policy_version": "1.2.0",
        "calibration_split": "CALIB (grouped by image_id)",
        "test_split": "TEST (grouped by image_id)",
        "isolation_forest_version": "v1.2.0_dev_tp_only",
        "decision_semantics": {
            "confirm": "automatic positive classification when enabled and threshold met",
            "review": "possible target requiring human verification",
            "unknown": "atypical known-positive evidence profile",
            "low_evidence": "insufficient evidence for current prioritization"
        },
        "uncalibrated_classes": ["submarine_pipeline", "ghost_net"],
        "class_policies": policy.get("classes", {})
    }
    with open(r"E:\GITHUB\a sih 2026\ai\reliability\weights\gate_e_manifest.json", 'w') as f:
        json.dump(manifest, f, indent=4)
        
    print("\nGate E.2 Reliability Sign-off complete. Manifest written.")

if __name__ == "__main__":
    run_gate_e2_reliability()
