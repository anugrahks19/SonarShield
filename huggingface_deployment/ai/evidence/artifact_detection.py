import numpy as np

def extract_artifact_flags(image_gray, bbox):
    """
    Checks for sonar artifacts or boundary conditions.
    """
    h, w = image_gray.shape
    x1, y1, x2, y2 = map(int, bbox)
    
    flags = {
        "near_image_edge": False,
        "near_nadir": False,
        "dropout": False,
        "extreme_saturation": False,
        "very_low_dynamic_range": False
    }
    
    # 1. Near image edge
    margin = 15
    if x1 < margin or y1 < margin or x2 > w - margin or y2 > h - margin:
        flags["near_image_edge"] = True
        
    # 2. Near nadir
    if x1 < 50 or x2 > w - 50:
        flags["near_nadir"] = True
        
    # Get object region
    obj_x1, obj_y1 = max(0, x1), max(0, y1)
    obj_x2, obj_y2 = min(w, x2), min(h, y2)
    if obj_x2 > obj_x1 and obj_y2 > obj_y1:
        roi = image_gray[obj_y1:obj_y2, obj_x1:obj_x2]
        
        # 3. Dropout (pure black region)
        if np.mean(roi) < 5.0:
            flags["dropout"] = True
            
        # 4. Extreme saturation (pure white region)
        if np.mean(roi) > 240.0:
            flags["extreme_saturation"] = True
            
        # 5. Very low dynamic range (flat texture)
        if np.std(roi) < 2.0:
            flags["very_low_dynamic_range"] = True
            
    return {"artifact_flags": flags}
