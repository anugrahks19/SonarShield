import cv2
from .object_geometry import extract_object_geometry
from .seabed_context import extract_seabed_context
from .shadow_analysis import extract_shadow_evidence
from .boundary_analysis import extract_boundary_evidence
from .artifact_detection import extract_artifact_flags

def extract_all_evidence(image, candidate):
    """
    Extracts deterministic physical evidence around a given detection candidate.
    image: numpy array (BGR or Grayscale) of the original un-preprocessed image.
    candidate: dict containing 'class', 'detector_confidence', 'bbox', 'source'
    """
    if len(image.shape) == 3:
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image
        
    bbox = candidate['bbox']
    
    # 1. Object Geometry
    geometry = extract_object_geometry(bbox)
    
    # 2. Seabed Context
    seabed = extract_seabed_context(image_gray, bbox)
    
    # 3. Shadow Evidence
    shadow = extract_shadow_evidence(image_gray, bbox, seabed['background_mean'], seabed['background_std'])
    
    # 4. Boundary Strength
    boundary = extract_boundary_evidence(image_gray, bbox, seabed['background_mean'])
    
    # 5. Artifacts
    artifacts = extract_artifact_flags(image_gray, bbox)
    
    return {
        "class": candidate['class'],
        "confidence": float(candidate['detector_confidence']),
        "source": candidate['source'],
        "bbox": candidate['bbox'],
        
        "object": {
            "bbox_area_px": geometry['bbox_area_px'],
            "width_px": geometry['width_px'],
            "height_px": geometry['height_px'],
            "aspect_ratio": geometry['aspect_ratio']
        },
        
        "seabed": {
            "mean_intensity": seabed['background_mean'],
            "std_intensity": seabed['background_std'],
            "local_contrast": seabed['local_contrast']
        },
        
        "shadow": {
            "shadow_candidate_presence": shadow['shadow_candidate_presence'],
            "area_ratio": shadow['area_ratio'],
            "mean_intensity_ratio": shadow['mean_intensity_ratio'],
            "adjacency": shadow['adjacency'],
            "shadow_bbox": shadow['shadow_bbox'] # kept for visual auditing
        },
        
        "quality": {
            "boundary_strength": boundary['boundary_strength'],
            "artifact_flags": artifacts["artifact_flags"]
        }
    }
