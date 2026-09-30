import numpy as np
import cv2

def extract_seabed_context(image_gray, bbox, ring_padding=20):
    """
    Extracts statistical context from the object region and its immediate surrounding seabed ring.
    image_gray: Source image in grayscale.
    bbox: [x1, y1, x2, y2]
    ring_padding: pixels to expand for the outer ring
    """
    h, w = image_gray.shape
    x1, y1, x2, y2 = map(int, bbox)
    
    # Clip object bbox to image boundaries
    obj_x1, obj_y1 = max(0, x1), max(0, y1)
    obj_x2, obj_y2 = min(w, x2), min(h, y2)
    
    if obj_x2 <= obj_x1 or obj_y2 <= obj_y1:
        return _empty_seabed_stats()
        
    object_roi = image_gray[obj_y1:obj_y2, obj_x1:obj_x2]
    
    # Outer ring bbox
    ring_x1 = max(0, x1 - ring_padding)
    ring_y1 = max(0, y1 - ring_padding)
    ring_x2 = min(w, x2 + ring_padding)
    ring_y2 = min(h, y2 + ring_padding)
    
    # Create a mask for the outer ring
    # Outer box is 1, inner object is 0
    ring_mask = np.ones((ring_y2 - ring_y1, ring_x2 - ring_x1), dtype=np.uint8)
    
    inner_rel_x1 = obj_x1 - ring_x1
    inner_rel_y1 = obj_y1 - ring_y1
    inner_rel_x2 = obj_x2 - ring_x1
    inner_rel_y2 = obj_y2 - ring_y1
    
    if inner_rel_x2 > inner_rel_x1 and inner_rel_y2 > inner_rel_y1:
        ring_mask[inner_rel_y1:inner_rel_y2, inner_rel_x1:inner_rel_x2] = 0
        
    ring_roi = image_gray[ring_y1:ring_y2, ring_x1:ring_x2]
    ring_pixels = ring_roi[ring_mask == 1]
    
    object_mean = float(np.mean(object_roi)) if object_roi.size > 0 else 0.0
    object_std = float(np.std(object_roi)) if object_roi.size > 0 else 0.0
    
    background_mean = float(np.mean(ring_pixels)) if ring_pixels.size > 0 else 0.0
    background_std = float(np.std(ring_pixels)) if ring_pixels.size > 0 else 0.0
    
    # Local contrast: commonly |I_obj - I_bg| / (I_obj + I_bg) or similar
    denom = (object_mean + background_mean)
    local_contrast = abs(object_mean - background_mean) / denom if denom > 0 else 0.0

    return {
        "object_mean": object_mean,
        "object_std": object_std,
        "background_mean": background_mean,
        "background_std": background_std,
        "local_contrast": local_contrast
    }

def _empty_seabed_stats():
    return {
        "object_mean": 0.0,
        "object_std": 0.0,
        "background_mean": 0.0,
        "background_std": 0.0,
        "local_contrast": 0.0
    }
