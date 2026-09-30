import os
import sys
import unittest
import tempfile
import json
from pydantic import ValidationError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gates.gate_f6_provenance_quality import GateF6Processor, compute_sha256
from api.f6_schema import QualityReport, ProvenanceRecord

class TestGateF6(unittest.TestCase):
    def setUp(self):
        # Create a dummy model artifact to hash
        self.temp_model = tempfile.NamedTemporaryFile(delete=False)
        self.temp_model.write(b"dummy_model_weights")
        self.temp_model.close()
        
        self.temp_image = tempfile.NamedTemporaryFile(delete=False)
        self.temp_image.write(b"dummy_image_data")
        self.temp_image.close()

        self.processor = GateF6Processor(config={
            "pipeline_version": "v1.2",
            "detector_artifact_path": self.temp_model.name
        })

    def tearDown(self):
        os.unlink(self.temp_model.name)
        os.unlink(self.temp_image.name)

    def test_provenance_hash_reproducibility(self):
        prov1 = self.processor.extract_provenance(
            candidate_id="CAND-001",
            input_id="IMG-001",
            image_path=self.temp_image.name,
            dataset_name="TEST_DATA"
        )
        prov2 = self.processor.extract_provenance(
            candidate_id="CAND-002",
            input_id="IMG-001",
            image_path=self.temp_image.name,
            dataset_name="TEST_DATA"
        )
        
        # Hashes should be perfectly reproducible for the same file
        self.assertEqual(prov1.image_sha256, prov2.image_sha256)
        self.assertEqual(prov1.detector_artifact_sha256, prov2.detector_artifact_sha256)
        self.assertNotEqual(prov1.image_sha256, "UNKNOWN_HASH")
        
        # Validate schema
        self.assertEqual(prov1.pipeline_version, "v1.2")
        self.assertIn("processing_timestamp", prov1.model_dump())

    def test_quality_flags_missing_metadata(self):
        evidence = {
            "bbox": [10, 10, 50, 50],
            "seabed": {"local_contrast": 0.8},
            "quality": {"boundary_strength": 0.9, "artifact_flags": {"is_noisy": False}},
            "shadow": {"shadow_candidate_presence": 1.0, "area_ratio": 0.5}
        }
        metadata = {} # Empty metadata -> missing geo/nav
        
        report = self.processor.assess_quality(
            evidence=evidence,
            localization_status="PIXEL_ONLY",
            metadata=metadata,
            image_w=100,
            image_h=100
        )
        
        # Test PIXEL_ONLY warning
        loc_codes = [f.code for f in report.localization.flags]
        self.assertIn("PIXEL_ONLY", loc_codes)
        
        # Test metadata missing warnings
        meta_codes = [f.code for f in report.metadata.flags]
        self.assertIn("MISSING_NAVIGATION", meta_codes)
        self.assertIn("MISSING_SENSOR_POSE", meta_codes)

    def test_quality_flags_low_quality_image(self):
        evidence = {
            "bbox": [0, 0, 100, 100], # edge of image
            "seabed": {"local_contrast": 0.1}, # low contrast
            "quality": {"boundary_strength": 0.2, "artifact_flags": {"is_noisy": True}}, # noisy, weak boundary
            "shadow": {"shadow_candidate_presence": 0.0} # missing shadow
        }
        
        report = self.processor.assess_quality(
            evidence=evidence,
            localization_status="GEOGRAPHIC",
            metadata={"time_aligned_navigation": True, "sensor_lever_arm": True, "geodetic_crs": True},
            image_w=100,
            image_h=100
        )
        
        # Image flags
        img_codes = [f.code for f in report.image.flags]
        self.assertIn("LOW_CONTRAST", img_codes)
        self.assertIn("HIGH_NOISE", img_codes)
        
        # Detection flags
        det_codes = [f.code for f in report.detection.flags]
        self.assertIn("EDGE_OF_IMAGE", det_codes)
        self.assertIn("LOW_BOUNDARY_STRENGTH", det_codes)
        
        # Evidence flags
        ev_codes = [f.code for f in report.evidence.flags]
        self.assertIn("MISSING_SHADOW_SUPPORT", ev_codes)
        
        # Evidence completeness
        self.assertIn("SHADOW", report.evidence.completeness.missing)
        self.assertIn("BOUNDARY", report.evidence.completeness.available)

if __name__ == '__main__':
    unittest.main()
