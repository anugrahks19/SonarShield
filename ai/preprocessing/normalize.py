import cv2
import numpy as np

def percentile_normalize(image, lower_percentile=1.0, upper_percentile=99.0):
    """
    Clips the image intensities at the given percentiles and normalizes to 0-255.
    Useful for removing bright acoustic anomalies and dark dropout noise before processing.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    lower_val = np.percentile(gray, lower_percentile)
    upper_val = np.percentile(gray, upper_percentile)

    clipped = np.clip(image, lower_val, upper_val)
    normalized = cv2.normalize(clipped, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    return normalized
