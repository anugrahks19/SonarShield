import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.coordinate_schema import (
    GeolocationContract, LocalizationStatus, CoordinatesPayload,
    ImageCoordinates, NormalizedImageCoordinates, ImageGeometry, PixelConvention
)

class TestF2CoordinateContract(unittest.TestCase):
    def test_case_c_pixel_only(self):
        # Emulate the standard benchmark dataset scenario (Gate F1 -> PIXEL_ONLY)
        payload = GeolocationContract(
            localization_status=LocalizationStatus.PIXEL_ONLY,
            reason="No navigation metadata",
            image_geometry=ImageGeometry(
                original_width_px=1920, original_height_px=1080,
                model_width_px=640, model_height_px=640,
                scale=0.333, pad_x=0.0, pad_y=120.0
            ),
            coordinates=CoordinatesPayload(
                image=ImageCoordinates(
                    x_min=100, y_min=100, x_max=200, y_max=200,
                    center_x=150, center_y=150, width_px=100, height_px=100
                ),
                normalized_image=NormalizedImageCoordinates(
                    center_x=0.5, center_y=0.5, width_norm=0.1, height_norm=0.1
                ),
                sonar=None,
                geographic=None
            )
        )
        
        self.assertEqual(payload.localization_status, LocalizationStatus.PIXEL_ONLY)
        self.assertIsNotNone(payload.coordinates.image)
        self.assertIsNone(payload.coordinates.geographic)
        self.assertIsNone(payload.coordinates.sonar)
        
        # Test serialization to ensure NO fake (0,0) coordinates appear for geographic
        json_data = payload.model_dump()
        self.assertIsNone(json_data['coordinates']['geographic'])
        self.assertEqual(json_data['pixel_convention']['origin'], "top-left")
        
    def test_case_unavailable(self):
        # Empty detection or invalid inference
        payload = GeolocationContract(
            localization_status=LocalizationStatus.UNAVAILABLE,
            reason="No valid spatial localization can be provided for this output",
            coordinates=CoordinatesPayload(
                image=None,
                normalized_image=None,
                sonar=None,
                geographic=None
            )
        )
        self.assertIsNone(payload.coordinates.image)
        self.assertEqual(payload.localization_status, LocalizationStatus.UNAVAILABLE)
        
if __name__ == '__main__':
    unittest.main()
