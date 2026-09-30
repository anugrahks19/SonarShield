import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.gate_f8_api_server import app

client = TestClient(app)

class TestGateF8(unittest.TestCase):
    
    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["schema_version"], "F8.0")
        self.assertIn("components", data)
        
    def test_analyze_endpoint(self):
        # Create a dummy image file
        with open("test_image.jpg", "wb") as f:
            f.write(b"dummy")
            
        with open("test_image.jpg", "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("test_image.jpg", f, "image/jpeg")},
                data={"run_tiled_auxiliary": "true", "return_visual_audit": "true"}
            )
            
        os.remove("test_image.jpg")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["schema_version"], "F8.0")
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["input"]["filename"], "test_image.jpg")
        self.assertIn("visual_audit_url", data["artifacts"])

if __name__ == '__main__':
    unittest.main()
