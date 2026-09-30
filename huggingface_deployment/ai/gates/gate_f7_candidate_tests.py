import os
import sys
import unittest
import json
from pydantic import ValidationError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.candidate_schema import Candidate
from api.f6_schema import ProvenanceRecord, QualityReport, ImageQuality, QualityFlag
from api.classification_schema import ClassificationPayload, ReliabilityEstimate, PresentationPolicy, ConfidenceInterval
from api.coordinate_schema import (
    LocalizationMetadata, LocalizationStatus, PixelConvention, CoordinatesPayload, ImageCoordinates,
    ErrorEnvelopeReference, LocalizationValidation
)

def create_base_candidate(candidate_id="CAND-001", decision_status="REVIEW", loc_status=LocalizationStatus.PIXEL_ONLY):
    return {
        "candidate_id": candidate_id,
        "detection": {
            "class_id": 1,
            "class_name": "Wreck",
            "confidence": 0.85,
            "bbox": [10.0, 10.0, 50.0, 50.0],
            "source_mode": "GLOBAL"
        },
        "classification": {
            "class_id": 1,
            "class_name": "Wreck",
            "reliability": {
                "estimated_tp_rate": 0.857,
                "support_count": 98,
                "method": "CLASS_CONDITIONAL_EMPIRICAL_BINNING",
                "source_split": "CALIB",
                "confidence_interval": {"lower": 0.7, "upper": 0.9}
            },
            "presentation": {
                "reliability_band": "HIGH_RELIABILITY",
                "uncertainty_level": "LOW_UNCERTAINTY"
            }
        },
        "decision": {
            "status": decision_status,
            "fusion_score": 0.65,
            "reason_codes": ["FUSION_ABOVE_REVIEW_THRESHOLD"]
        },
        "evidence": {
            "ai_confidence": 0.85,
            "bbox": [10, 10, 50, 50],
            "geometry": {
                "width_px": 40,
                "height_px": 40,
                "bbox_area_px": 1600,
                "aspect_ratio": 1.0
            },
            "seabed": {
                "background_mean": 92.1,
                "background_std": 17.4,
                "local_contrast": 0.65
            },
            "shadow": {
                "shadow_candidate_presence": 0.71,
                "shadow_area_px": 420.0,
                "area_ratio": 0.26,
                "adjacency": 0.88,
                "mean_intensity_ratio": 0.3
            },
            "quality": {
                "boundary_strength": 0.8,
                "artifact_flags": {}
            }
        },
        "localization": {
            "metadata": {
                "status": loc_status,
                "available_spaces": ["IMAGE_PIXEL"] if loc_status != LocalizationStatus.UNAVAILABLE else [],
                "unavailable_spaces": ["SONAR_RELATIVE", "GEOGRAPHIC"],
                "reason_code": "NO_SONAR_NAV_METADATA"
            },
            "pixel_convention": {},
            "coordinate_provenance": [],
            "coordinates": {
                "image": {
                    "x_min": 10.0, "y_min": 10.0, "x_max": 50.0, "y_max": 50.0,
                    "center_x": 30.0, "center_y": 30.0, "width_px": 40.0, "height_px": 40.0
                }
            } if loc_status != LocalizationStatus.UNAVAILABLE else {}
        },
        "localization_uncertainty": {
            "validation_reference": {
                "scope": "CLASS_LEVEL",
                "class_name": "Wreck",
                "median_center_error_px": 75.5,
                "p90_center_error_px": 130.2,
                "median_normalized_center_error": 0.11,
                "p90_normalized_center_error": 0.19
            },
            "error_envelope": {
                "status": "CLASS_CONDITIONAL_ESTIMATE",
                "scope": "CLASS_CONDITIONAL",
                "method": "CALIB_DERIVED_P90_ENVELOPE",
                "envelope_px": 130.2,
                "envelope_normalized": 0.19,
                "reason": "Bounded to 90th percentile of CALIB set validation"
            }
        },
        "quality": {
            "image": {"flags": []},
            "detection": {"flags": []},
            "evidence": {"completeness": {"available": ["AI"], "missing": ["SHADOW"]}, "flags": []},
            "localization": {"flags": [{"code": "PIXEL_ONLY", "severity": "WARNING"}]},
            "metadata": {"flags": []}
        },
        "provenance": {
            "candidate_id": candidate_id,
            "input_id": "IMG-123",
            "source_dataset": "Test",
            "image_sha256": "abcdef...",
            "pipeline_version": "v1.0",
            "detector_version": "V6-P2",
            "fusion_version": "D2-v1",
            "decision_policy_version": "E1-v1",
            "calibration_version": "F5-1.0",
            "preprocessing_version": "v1.0",
            "coordinate_contract_version": "F3-1.0",
            "detector_artifact_sha256": "hash",
            "fusion_artifact_sha256": "hash",
            "decision_policy_sha256": "hash",
            "classification_calibration_sha256": "hash",
            "localization_uncertainty_sha256": "hash",
            "processing_timestamp": "2026-09-30T10:00:00Z",
            "runtime_version": "python3"
        }
    }

class TestGateF7(unittest.TestCase):
    
    def test_normal_review_candidate(self):
        data = create_base_candidate(decision_status="REVIEW")
        cand = Candidate(**data)
        self.assertEqual(cand.decision.status, "REVIEW")
        self.assertEqual(cand.localization.metadata.status, LocalizationStatus.PIXEL_ONLY)
        
        # Serialization / Deserialization
        json_data = cand.model_dump_json()
        cand2 = Candidate.model_validate_json(json_data)
        self.assertEqual(cand.candidate_id, cand2.candidate_id)
        
    def test_unknown_candidate(self):
        data = create_base_candidate(decision_status="UNKNOWN")
        cand = Candidate(**data)
        self.assertEqual(cand.decision.status, "UNKNOWN")
        
    def test_pipeline_ghost_forced_review(self):
        data = create_base_candidate(decision_status="REVIEW")
        data["classification"]["class_name"] = "Pipeline"
        data["classification"]["reliability"]["estimated_tp_rate"] = 0.0
        data["classification"]["presentation"]["reliability_band"] = "UNCALIBRATED"
        cand = Candidate(**data)
        self.assertEqual(cand.classification.presentation.reliability_band, "UNCALIBRATED")
        
    def test_missing_metadata(self):
        data = create_base_candidate()
        data["quality"]["metadata"]["flags"].append({"code": "MISSING_NAVIGATION", "severity": "WARNING"})
        cand = Candidate(**data)
        self.assertEqual(cand.quality.metadata.flags[0].code, "MISSING_NAVIGATION")

if __name__ == '__main__':
    unittest.main()
