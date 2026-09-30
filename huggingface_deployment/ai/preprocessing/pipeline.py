import cv2
import numpy as np
from .normalize import percentile_normalize
from .denoise import apply_denoise
from .clahe import apply_clahe

def preprocess_sonar_image(image_path_or_array, normalize=False, denoise_method="none", use_clahe=False):
    """
    Configurable preprocessing pipeline for Side Scan Sonar images.
    Takes either a file path or a loaded numpy array.
    """
    if isinstance(image_path_or_array, str):
        image = cv2.imread(image_path_or_array)
        if image is None:
            raise ValueError(f"Could not read image at {image_path_or_array}")
    else:
        image = image_path_or_array
        
    processed = image.copy()
    
    if normalize:
        processed = percentile_normalize(processed)
        
    if denoise_method and denoise_method.lower() != "none":
        processed = apply_denoise(processed, method=denoise_method)
        
    if use_clahe:
        processed = apply_clahe(processed)
        
    return processed
