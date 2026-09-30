import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.coordinate_schema import ImageGeometry, LocalizationStatus
from api.coordinate_adapter import CoordinateAdapter

class TestCoordinateAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = CoordinateAdapter()
        # Original: 1920x1080. Scaled to 640x640 letterbox.
        # Scale = 640 / 1920 = 0.333333333333.
        # new width = 640. new height = 1080 * 0.3333 = 360
        # padding y = (640 - 360) / 2 = 140
        self.geom = ImageGeometry(
            original_width_px=1920,
            original_height_px=1080,
            model_width_px=640,
            model_height_px=640,
            transform="LETTERBOX",
            scale_x=1/3.0,
            scale_y=1/3.0,
            pad_left_px=0.0,
            pad_top_px=140.0,
            pad_right_px=0.0,
            pad_bottom_px=140.0
        )
        
    def test_unavailable_when_no_box(self):
        res = self.adapter.transform(None, "MODEL_PIXEL", self.geom)
        self.assertEqual(res.localization.status, LocalizationStatus.UNAVAILABLE)
        self.assertEqual(res.localization.reason_code, "NO_DETECTION")
        self.assertIsNone(res.coordinates.image)

    def test_not_processed(self):
        res = self.adapter.transform((100, 200, 200, 300), "IMAGE_PIXEL", self.geom, candidate_processed=False)
        self.assertEqual(res.localization.status, LocalizationStatus.NOT_PROCESSED)
        self.assertEqual(res.localization.reason_code, "CANDIDATE_NOT_PROCESSED")
        self.assertIsNone(res.coordinates.image)

    def test_model_to_image_pixel(self):
        # Center crop in model space: [100, 200, 200, 300]
        # Reverse y pad: 200-140=60, 300-140=160
        # Reverse scale: 100/(1/3) = 300, 60/(1/3) = 180, 200/(1/3)=600, 160/(1/3)=480
        res = self.adapter.transform((100, 200, 200, 300), "MODEL_PIXEL", self.geom)
        
        self.assertEqual(res.localization.status, LocalizationStatus.PIXEL_ONLY)
        self.assertEqual(res.localization.reason_code, "NO_SONAR_NAV_METADATA")
        self.assertIsNotNone(res.coordinates.image)
        img_c = res.coordinates.image
        self.assertAlmostEqual(img_c.x_min, 300.0)
        self.assertAlmostEqual(img_c.y_min, 180.0)
        self.assertAlmostEqual(img_c.x_max, 600.0)
        self.assertAlmostEqual(img_c.y_max, 480.0)
        
        # Test provenance
        prov = res.coordinate_provenance[0]
        self.assertEqual(prov.source_space, "MODEL_PIXEL")
        self.assertEqual(prov.target_space, "IMAGE_PIXEL")
        self.assertEqual(prov.transform, "INVERSE_LETTERBOX")

    def test_already_image_pixel(self):
        # Already IMAGE_PIXEL
        res = self.adapter.transform((300, 180, 600, 480), "IMAGE_PIXEL", self.geom)
        self.assertEqual(res.localization.status, LocalizationStatus.PIXEL_ONLY)
        img_c = res.coordinates.image
        self.assertEqual(img_c.x_min, 300.0)
        
        # Provenance
        prov = res.coordinate_provenance[0]
        self.assertEqual(prov.source_space, "IMAGE_PIXEL")
        self.assertEqual(prov.target_space, "IMAGE_PIXEL")
        self.assertEqual(prov.transform, "IDENTITY")

    def test_round_trip(self):
        boxes = [
            (0, 0, 100, 100), # Top-left
            (1820, 0, 1920, 100), # Top-right
            (0, 980, 100, 1080), # Bottom-left
            (1820, 980, 1920, 1080), # Bottom-right
            (910, 530, 1010, 550), # Center
            (600, 300, 900, 600), # Synthetic known
        ]
        
        for box in boxes:
            x1, y1, x2, y2 = box
            # Forward transform (simulate what YOLO dataloader does)
            mx1 = x1 * self.geom.scale_x + self.geom.pad_left_px
            my1 = y1 * self.geom.scale_y + self.geom.pad_top_px
            mx2 = x2 * self.geom.scale_x + self.geom.pad_left_px
            my2 = y2 * self.geom.scale_y + self.geom.pad_top_px
            
            # Inverse transform via Adapter
            res = self.adapter.transform((mx1, my1, mx2, my2), "MODEL_PIXEL", self.geom)
            img_c = res.coordinates.image
            
            # Assert round trip success
            self.assertAlmostEqual(img_c.x_min, float(x1), places=3)
            self.assertAlmostEqual(img_c.y_min, float(y1), places=3)
            self.assertAlmostEqual(img_c.x_max, float(x2), places=3)
            self.assertAlmostEqual(img_c.y_max, float(y2), places=3)
            
    def test_clipping(self):
        # A box that extends outside model space bounds should be clipped to original image
        res = self.adapter.transform((-10, -50, 700, 1000), "MODEL_PIXEL", self.geom)
        img_c = res.coordinates.image
        self.assertEqual(img_c.x_min, 0.0)
        self.assertEqual(img_c.y_min, 0.0)
        self.assertEqual(img_c.x_max, 1920.0) # max original width
        self.assertEqual(img_c.y_max, 1080.0) # max original height

    def test_future_geo_capability(self):
        metadata = {
            "pixel_to_range_model": True,
            "across_track_geometry": True,
            "towfish_altitude": 10.0,
            "time_aligned_navigation": True,
            "sensor_lever_arm": True,
            "geodetic_crs": "WGS84",
            "towfish_pose": True
        }
        res = self.adapter.transform((100, 200, 200, 300), "IMAGE_PIXEL", self.geom, metadata)
        self.assertEqual(res.localization.status, LocalizationStatus.GEOGRAPHIC)
        self.assertIn("GEOGRAPHIC", res.localization.available_spaces)
        self.assertIn("SONAR_RELATIVE", res.localization.available_spaces)

if __name__ == '__main__':
    unittest.main()
