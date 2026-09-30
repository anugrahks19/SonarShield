import os
import json
import numpy as np
import sys
import math
from collections import defaultdict
from sklearn.model_selection import GroupShuffleSplit

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fusion.gate_d2_final import load_ground_truth, compute_iou, denormalize_box

def get_center_w_h(box):
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w/2.0
    cy = y1 + h/2.0
    return cx, cy, w, h

def run_f4_localization():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    val_labels_dir = r"E:\GITHUB\a sih 2026\datasets\gate_a_SOURCE_STATE_UNKNOWN\labels\val"
    
    with open(results_file, 'r') as f: data = json.load(f)
    gt_boxes = load_ground_truth(val_labels_dir)
    
    groups = []
    for item in data:
        groups.append(item['image_id'])
    
    groups = np.array(groups)
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=42)
    dev_idx, temp_idx = next(gss1.split(groups, groups, groups=groups))
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    calib_idx_local, test_idx_local = next(gss2.split(groups[temp_idx], groups[temp_idx], groups=groups[temp_idx]))
    
    calib_idx = temp_idx[calib_idx_local]
    test_idx = temp_idx[test_idx_local]
    
    calib_data = [data[i] for i in calib_idx]
    test_data = [data[i] for i in test_idx]
    
    class_map = {0: "Crab Pot", 1: "Wreck", 2: "Mine", 3: "Pipeline", 4: "Ghost Net"}
    
    def process_split(split_data):
        metrics_by_class = defaultdict(lambda: {
            "center_error_px": [],
            "normalized_center_error": [],
            "iou": []
        })
        matched = 0
        total_gt = 0
        
        # Keep track of ground truth to ensure 1-to-1 matching
        # (Though we just do a greedy match for simplicity here, 
        # a true 1-to-1 should track which GT was assigned)
        
        # First count total GT in this split
        split_image_ids = set([item['image_id'] for item in split_data])
        for img_id in split_image_ids:
            if img_id in gt_boxes:
                total_gt += len(gt_boxes[img_id])
                
        # To enforce 1-to-1, we sort predictions by confidence and assign to highest IoU GT
        # that hasn't been claimed yet.
        predictions_by_img = defaultdict(list)
        for item in split_data:
            predictions_by_img[item['image_id']].append(item['evidence'])
            
        for img_id in split_image_ids:
            if img_id not in gt_boxes: continue
            
            img_preds = sorted(predictions_by_img[img_id], key=lambda x: x['confidence'], reverse=True)
            img_gts = [denormalize_box(b) for b in gt_boxes[img_id]]
            claimed_gts = set()
            
            for pred in img_preds:
                pred_box = pred['bbox']
                cls_id = pred['class']
                c_name = class_map.get(cls_id, str(cls_id))
                
                best_iou = 0
                best_gt_idx = -1
                for idx, gt_box in enumerate(img_gts):
                    if idx in claimed_gts: continue
                    iou = compute_iou(pred_box, gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = idx
                        
                if best_iou >= 0.50:
                    claimed_gts.add(best_gt_idx)
                    matched += 1
                    
                    gt_box = img_gts[best_gt_idx]
                    pcx, pcy, pw, ph = get_center_w_h(pred_box)
                    gcx, gcy, gw, gh = get_center_w_h(gt_box)
                    
                    center_dist = math.hypot(pcx - gcx, pcy - gcy)
                    gt_diag = math.hypot(gw, gh)
                    norm_err = center_dist / gt_diag if gt_diag > 0 else 0
                    
                    metrics_by_class[c_name]["center_error_px"].append(center_dist)
                    metrics_by_class[c_name]["normalized_center_error"].append(norm_err)
                    metrics_by_class[c_name]["iou"].append(best_iou)
                    
        return metrics_by_class, total_gt, matched

    # 1. Fit Envelope on CALIB
    calib_metrics, calib_total_gt, calib_matched = process_split(calib_data)
    envelope = {}
    print("\n--- GATE F4.1: CALIB SPLIT (FITTING LOCALIZATION ENVELOPE) ---")
    for c_name, mets in calib_metrics.items():
        if len(mets["iou"]) == 0: continue
        p90_px = np.percentile(mets["center_error_px"], 90)
        p90_norm = np.percentile(mets["normalized_center_error"], 90)
        envelope[c_name] = {
            "p90_error_px": float(p90_px),
            "p90_error_norm": float(p90_norm),
            "median_error_px": float(np.median(mets["center_error_px"])),
            "median_error_norm": float(np.median(mets["normalized_center_error"]))
        }
        print(f"Class: {c_name} | P90 Error: {p90_px:.1f}px ({p90_norm*100:.1f}% of object scale)")

    # 2. Evaluate Coverage on TEST
    test_metrics, test_total_gt, test_matched = process_split(test_data)
    print("\n--- GATE F4.2: TEST SPLIT (EVALUATING COVERAGE) ---")
    print(f"Total Ground Truth Targets : {test_total_gt}")
    print(f"Matched Detections         : {test_matched} (Coverage: {test_matched/test_total_gt*100:.1f}%)")
    print("Note: Localization error is measured ONLY among matched detections.\n")
    
    for c_name, mets in test_metrics.items():
        if len(mets["iou"]) == 0: continue
        if c_name not in envelope: continue
        
        env_px = envelope[c_name]["p90_error_px"]
        env_norm = envelope[c_name]["p90_error_norm"]
        
        # Calculate coverage (how many test samples fall within the P90 calib envelope)
        px_coverage = np.mean(np.array(mets["center_error_px"]) <= env_px) * 100
        norm_coverage = np.mean(np.array(mets["normalized_center_error"]) <= env_norm) * 100
        
        print(f"Class: {c_name} (N={len(mets['iou'])} matched)")
        print(f"  Test Median Error : {np.median(mets['center_error_px']):.1f}px ({np.median(mets['normalized_center_error'])*100:.1f}% scale)")
        print(f"  Envelope (from CALIB): {env_px:.1f}px ({env_norm*100:.1f}% scale)")
        print(f"  Test Coverage        : {norm_coverage:.1f}% of matched test detections fell within the CALIB envelope.")

    os.makedirs(r"E:\GITHUB\a sih 2026\ai\reliability\weights", exist_ok=True)
    with open(r"E:\GITHUB\a sih 2026\ai\reliability\weights\localization_envelope.json", 'w') as f:
        json.dump(envelope, f, indent=4)

if __name__ == "__main__":
    run_f4_localization()
