import numpy as np

def extract_object_geometry(bbox, mask=None):
    """
    Extracts geometric features from the bounding box (and optionally object mask).
    bbox: [x1, y1, x2, y2]
    mask: Optional boolean numpy array of the object shape.
    """
    x1, y1, x2, y2 = bbox
    width_px = x2 - x1
    height_px = y2 - y1
    bbox_area_px = width_px * height_px
    
    # Avoid division by zero
    aspect_ratio = width_px / height_px if height_px > 0 else 0
    center_x = x1 + width_px / 2
    center_y = y1 + height_px / 2

    return {
        "width_px": float(width_px),
        "height_px": float(height_px),
        "bbox_area_px": float(bbox_area_px),
        "aspect_ratio": float(aspect_ratio),
        "center_x": float(center_x),
        "center_y": float(center_y)
    }
