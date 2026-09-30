import cv2

def apply_clahe(image, clip_limit=2.0, tile_grid_size=(8, 8)):
    """
    Applies Contrast Limited Adaptive Histogram Equalization.
    Enhances local contrast, which can help emphasize acoustic shadows.
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    if len(image.shape) == 3:
        # Sonar is physically monochromatic, so we equalize the grayscale intensity
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        result = clahe.apply(gray)
        # Convert back to 3-channel for YOLO inference
        return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
    else:
        return clahe.apply(image)
