import numpy as np
import cv2

def extract_boundary_evidence(image_gray, bbox, bg_mean):
    """
    Measures edge strength and boundary contrast for the candidate.
    """
    h, w = image_gray.shape
    x1, y1, x2, y2 = map(int, bbox)
    
    # Pad by a small amount to get the boundary pixels
    pad = 5
    roi_x1 = max(0, x1 - pad)
    roi_y1 = max(0, y1 - pad)
    roi_x2 = min(w, x2 + pad)
    roi_y2 = min(h, y2 + pad)
    
    if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
        return _empty_boundary_stats()
        
    roi = image_gray[roi_y1:roi_y2, roi_x1:roi_x2]
    
    # Compute Sobel gradients
    grad_x = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    
    # We care about the gradient exactly at the boundary of the object
    # For a bounding box, the boundary is the perimeter of the box itself.
    rel_x1 = max(0, x1 - roi_x1)
    rel_y1 = max(0, y1 - roi_y1)
    rel_x2 = min(roi_x2 - roi_x1, x2 - roi_x1)
    rel_y2 = min(roi_y2 - roi_y1, y2 - roi_y1)
    
    # Create a boundary mask (e.g., 2 pixels thick around the bbox)
    mask = np.zeros(roi.shape, dtype=np.uint8)
    if rel_x2 > rel_x1 and rel_y2 > rel_y1:
        cv2.rectangle(mask, (rel_x1, rel_y1), (rel_x2, rel_y2), 255, thickness=2)
        
    boundary_pixels = grad_mag[mask == 255]
    boundary_intensities = roi[mask == 255]
    
    gradient_mean = float(np.mean(boundary_pixels)) if len(boundary_pixels) > 0 else 0.0
    
    # Edge strength relative to background standard deviation
    edge_strength = float(np.percentile(boundary_pixels, 90)) if len(boundary_pixels) > 0 else 0.0
    
    # Boundary contrast (difference between boundary intensity and background)
    boundary_mean_intensity = float(np.mean(boundary_intensities)) if len(boundary_intensities) > 0 else 0.0
    denom = (boundary_mean_intensity + bg_mean)
    boundary_contrast = abs(boundary_mean_intensity - bg_mean) / denom if denom > 0 else 0.0
    
    # A simplified boundary strength heuristic combining gradient and contrast
    # normalized approximately to 0-1 range
    normalized_grad = min(1.0, gradient_mean / 128.0)
    boundary_strength = 0.5 * normalized_grad + 0.5 * boundary_contrast

    return {
        "gradient_mean": gradient_mean,
        "edge_strength": edge_strength,
        "boundary_contrast": boundary_contrast,
        "boundary_strength": boundary_strength
    }

def _empty_boundary_stats():
    return {
        "gradient_mean": 0.0,
        "edge_strength": 0.0,
        "boundary_contrast": 0.0,
        "boundary_strength": 0.0
    }
