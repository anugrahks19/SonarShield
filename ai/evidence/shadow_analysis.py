import numpy as np
import cv2

def extract_shadow_evidence(image_gray, bbox, bg_mean, bg_std):
    """
    Identifies a shadow candidate region adjacent to the detection and calculates evidence.
    """
    h, w = image_gray.shape
    x1, y1, x2, y2 = map(int, bbox)
    
    obj_w = max(1, x2 - x1)
    obj_h = max(1, y2 - y1)
    
    # Define an extended ROI where the shadow might exist
    # Shadows usually fall laterally, so we pad heavily left/right and somewhat top/bottom
    pad_x = int(obj_w * 2.0)
    pad_y = int(obj_h * 1.0)
    
    roi_x1 = max(0, x1 - pad_x)
    roi_y1 = max(0, y1 - pad_y)
    roi_x2 = min(w, x2 + pad_x)
    roi_y2 = min(h, y2 + pad_y)
    
    if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
        return _empty_shadow_stats()
        
    roi = image_gray[roi_y1:roi_y2, roi_x1:roi_x2]
    
    # Shadow threshold: substantially darker than background
    # E.g., BG mean - 1.5*STD or absolute threshold
    thresh_val = max(10, bg_mean - 1.5 * bg_std)
    _, mask = cv2.threshold(roi, thresh_val, 255, cv2.THRESH_BINARY_INV)
    
    # Find connected components in the dark regions
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    best_shadow_label = -1
    best_shadow_score = -1
    
    # Object bbox within ROI coordinates
    rel_obj_x1 = max(0, x1 - roi_x1)
    rel_obj_y1 = max(0, y1 - roi_y1)
    rel_obj_x2 = min(roi_x2 - roi_x1, x2 - roi_x1)
    rel_obj_y2 = min(roi_y2 - roi_y1, y2 - roi_y1)
    
    bbox_area = obj_w * obj_h
    
    # Evaluate dark regions to find the best shadow candidate
    for i in range(1, num_labels):
        comp_area = stats[i, cv2.CC_STAT_AREA]
        if comp_area < 5:  # ignore noise
            continue
            
        comp_x1 = stats[i, cv2.CC_STAT_LEFT]
        comp_y1 = stats[i, cv2.CC_STAT_TOP]
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]
        comp_x2 = comp_x1 + comp_w
        comp_y2 = comp_y1 + comp_h
        
        # Calculate adjacency/distance to object
        dx = max(0, max(rel_obj_x1 - comp_x2, comp_x1 - rel_obj_x2))
        dy = max(0, max(rel_obj_y1 - comp_y2, comp_y1 - rel_obj_y2))
        distance = np.sqrt(dx*dx + dy*dy)
        
        if distance > obj_w * 0.5: # Must be somewhat adjacent
            continue
            
        # Score based on area and distance
        score = comp_area / (distance + 1.0)
        if score > best_shadow_score:
            best_shadow_score = score
            best_shadow_label = i
            
    if best_shadow_label == -1:
        return _empty_shadow_stats()
        
    shadow_mask = (labels == best_shadow_label)
    shadow_pixels = roi[shadow_mask]
    
    shadow_area_px = len(shadow_pixels)
    shadow_mean = float(np.mean(shadow_pixels))
    
    # Metrics
    area_ratio = shadow_area_px / bbox_area if bbox_area > 0 else 0
    mean_intensity_ratio = shadow_mean / bg_mean if bg_mean > 0 else 1.0
    
    # Distance of best shadow
    comp_x1 = stats[best_shadow_label, cv2.CC_STAT_LEFT]
    comp_y1 = stats[best_shadow_label, cv2.CC_STAT_TOP]
    comp_x2 = comp_x1 + stats[best_shadow_label, cv2.CC_STAT_WIDTH]
    comp_y2 = comp_y1 + stats[best_shadow_label, cv2.CC_STAT_HEIGHT]
    dx = max(0, max(rel_obj_x1 - comp_x2, comp_x1 - rel_obj_x2))
    dy = max(0, max(rel_obj_y1 - comp_y2, comp_y1 - rel_obj_y2))
    shadow_distance = float(np.sqrt(dx*dx + dy*dy))
    
    adjacency = max(0.0, 1.0 - (shadow_distance / (max(obj_w, obj_h) * 0.5)))
    
    # Shadow evidence score (composite heuristic)
    # A strong shadow is large, dark, and adjacent
    evidence_score = adjacency * min(1.0, area_ratio) * max(0.0, 1.0 - mean_intensity_ratio)
    
    # Compute perimeter for compactness
    contours, _ = cv2.findContours(shadow_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    perimeter = cv2.arcLength(contours[0], True) if len(contours) > 0 else 0
    shadow_compactness = (4 * np.pi * shadow_area_px) / (perimeter * perimeter) if perimeter > 0 else 0.0

    # Also compute relative box for visual auditing later
    shadow_bbox_global = [
        int(roi_x1 + comp_x1),
        int(roi_y1 + comp_y1),
        int(roi_x1 + comp_x2),
        int(roi_y1 + comp_y2)
    ]

    return {
        "shadow_area_px": float(shadow_area_px),
        "area_ratio": float(area_ratio),
        "shadow_mean": float(shadow_mean),
        "mean_intensity_ratio": float(mean_intensity_ratio),
        "adjacency": float(adjacency),
        "shadow_distance": float(shadow_distance),
        "shadow_compactness": float(shadow_compactness),
        "shadow_candidate_presence": float(evidence_score),
        "shadow_bbox": shadow_bbox_global
    }

def _empty_shadow_stats():
    return {
        "shadow_area_px": 0.0,
        "area_ratio": 0.0,
        "shadow_mean": 0.0,
        "mean_intensity_ratio": 1.0,
        "adjacency": 0.0,
        "shadow_distance": 999.0,
        "shadow_compactness": 0.0,
        "shadow_candidate_presence": 0.0,
        "shadow_bbox": None
    }
