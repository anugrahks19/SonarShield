import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gates.gate_f9_pipeline import SONAR_SHIELDPipeline

class TestGateF9(unittest.TestCase):
    def setUp(self):
        self.pipeline = SONAR_SHIELDPipeline()
        
    def test_normal_sss_image_flow(self):
        # 1. Normal SSS Image
        response = self.pipeline.process_image("test_image.jpg", {})
        self.assertEqual(response.status, "COMPLETED")
        self.assertEqual(response.summary["candidate_count"], 1)
        self.assertEqual(len(response.candidates), 1)
        
        # Verify Candidate
        cand = response.candidates[0]
        self.assertEqual(cand.decision.status, "REVIEW")
        
        # Verify F7/F8 internal consistency invariant
        total_counts = (response.summary["confirmed_count"] + 
                        response.summary["review_count"] + 
                        response.summary["rejected_count"] + 
                        response.summary["unknown_count"])
        self.assertEqual(response.summary["candidate_count"], total_counts)
        self.assertEqual(len(response.candidates), response.summary["candidate_count"])

    def test_unsupported_file(self):
        with self.assertRaises(ValueError) as context:
            self.pipeline.process_image("test_image.txt", {})
        self.assertEqual(str(context.exception), "UNSUPPORTED_FILE_TYPE")

if __name__ == '__main__':
    unittest.main()
