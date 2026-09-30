import cv2

def apply_denoise(image, method="bilateral"):
    """
    Applies noise reduction while preserving edges.
    Bilateral filtering is strongly recommended for Side Scan Sonar to preserve acoustic shadow edges.
    """
    if method == "bilateral":
        # d=9, sigmaColor=75, sigmaSpace=75 (standard safe defaults)
        return cv2.bilateralFilter(image, 9, 75, 75)
    elif method == "gaussian":
        return cv2.GaussianBlur(image, (5, 5), 0)
    elif method == "median":
        return cv2.medianBlur(image, 5)
    else:
        return image
