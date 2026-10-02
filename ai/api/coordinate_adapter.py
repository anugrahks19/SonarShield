from typing import Dict, Any, Optional, Tuple, List
import datetime
from ai.api.coordinate_schema import (
    GeolocationContract, LocalizationStatus, CoordinatesPayload, LocalizationMetadata,
    ImageCoordinates, NormalizedImageCoordinates, SonarCoordinates, GeographicCoordinates,
    ImageGeometry, PixelConvention, CoordinateProvenance,
    ErrorEnvelopeReference
)

class CoordinateAdapter:
    """
    Gate F3: Coordinate Transformation Layer.
    Transforms MODEL_PIXEL -> IMAGE_PIXEL -> SONAR_RELATIVE -> GEOGRAPHIC
    based on available metadata capability.
    """
    def __init__(self):
        self.pixel_convention = PixelConvention()

    def _reverse_letterbox(self, model_box: Tuple[float, float, float, float], geom: ImageGeometry) -> Tuple[float, float, float, float]:
        """
        Converts a box [x1, y1, x2, y2] from model space back to original image space.
        """
        mx1, my1, mx2, my2 = model_box
        
        # Remove padding
        x1 = mx1 - geom.pad_left_px
        y1 = my1 - geom.pad_top_px
        x2 = mx2 - geom.pad_left_px
        y2 = my2 - geom.pad_top_px
        
        # Reverse scale
        x1 /= geom.scale_x
        y1 /= geom.scale_y
        x2 /= geom.scale_x
        y2 /= geom.scale_y
        
        # Clip to original boundaries
        x1 = max(0.0, min(float(x1), float(geom.original_width_px)))
        y1 = max(0.0, min(float(y1), float(geom.original_height_px)))
        x2 = max(0.0, min(float(x2), float(geom.original_width_px)))
        y2 = max(0.0, min(float(y2), float(geom.original_height_px)))
        
        return x1, y1, x2, y2

    def transform(
        self, 
        input_box: Optional[Tuple[float, float, float, float]], 
        source_space: str,
        image_geometry: ImageGeometry, 
        metadata: Optional[Dict[str, Any]] = None,
        candidate_processed: bool = True
    ) -> GeolocationContract:
        """
        Executes the full transformation chain based on explicit metadata capability.
        """
        if metadata is None:
            metadata = {}
            
        provenance = []
        
        if not candidate_processed:
            return GeolocationContract(
                localization=LocalizationMetadata(
                    status=LocalizationStatus.NOT_PROCESSED,
                    available_spaces=[],
                    unavailable_spaces=["IMAGE_PIXEL", "SONAR_RELATIVE", "GEOGRAPHIC"],
                    reason_code="CANDIDATE_NOT_PROCESSED"
                ),
                image_geometry=image_geometry,
                coordinates=CoordinatesPayload(),
                localization_uncertainty=ErrorEnvelopeReference(
                    status="NOT_ESTIMABLE", reason="CANDIDATE_NOT_PROCESSED"
                )
            )

        if not input_box:
            return GeolocationContract(
                localization=LocalizationMetadata(
                    status=LocalizationStatus.UNAVAILABLE,
                    available_spaces=[],
                    unavailable_spaces=["IMAGE_PIXEL", "SONAR_RELATIVE", "GEOGRAPHIC"],
                    reason_code="NO_DETECTION"
                ),
                image_geometry=image_geometry,
                coordinates=CoordinatesPayload(),
                localization_uncertainty=ErrorEnvelopeReference(
                    status="NOT_ESTIMABLE", reason="NO_DETECTION"
                )
            )

        # 1. Resolve IMAGE_PIXEL
        if source_space == "MODEL_PIXEL":
            x1, y1, x2, y2 = self._reverse_letterbox(input_box, image_geometry)
            provenance.append(CoordinateProvenance(
                source_space="MODEL_PIXEL",
                target_space="IMAGE_PIXEL",
                transform="INVERSE_LETTERBOX",
                source_dimensions=[image_geometry.model_width_px, image_geometry.model_height_px],
                target_dimensions=[image_geometry.original_width_px, image_geometry.original_height_px]
            ))
        elif source_space == "IMAGE_PIXEL":
            x1, y1, x2, y2 = input_box
            provenance.append(CoordinateProvenance(
                source_space="IMAGE_PIXEL",
                target_space="IMAGE_PIXEL",
                transform="IDENTITY",
                source_dimensions=[image_geometry.original_width_px, image_geometry.original_height_px],
                target_dimensions=[image_geometry.original_width_px, image_geometry.original_height_px]
            ))
        else:
            raise ValueError(f"Unknown source space: {source_space}")

        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0
        
        image_coords = ImageCoordinates(
            x_min=x1, y_min=y1, x_max=x2, y_max=y2,
            center_x=cx, center_y=cy,
            width_px=w, height_px=h
        )
        
        norm_coords = NormalizedImageCoordinates(
            center_x=cx / image_geometry.original_width_px,
            center_y=cy / image_geometry.original_height_px,
            width_norm=w / image_geometry.original_width_px,
            height_norm=h / image_geometry.original_height_px
        )

        # 2. Assess Capabilities
        has_sonar = False
        has_geo = False
        if metadata:
            raise ValueError("Use the validated ground-range raster adapter; legacy metadata-presence checks cannot compute coordinates.")
        
        status = LocalizationStatus.PIXEL_ONLY
        reason_code = "NO_SONAR_NAV_METADATA"
        avail = ["IMAGE_PIXEL"]
        unavail = ["SONAR_RELATIVE", "GEOGRAPHIC"]
        
        sonar_coords = None
        geo_coords = None

        if has_sonar:
            status = LocalizationStatus.RELATIVE_SONAR
            reason_code = "NO_ABSOLUTE_GEO_METADATA"
            avail.append("SONAR_RELATIVE")
            unavail.remove("SONAR_RELATIVE")
            
        if has_geo:
            status = LocalizationStatus.GEOGRAPHIC
            reason_code = "FULL_LOCALIZATION"
            avail.append("GEOGRAPHIC")
            unavail.remove("GEOGRAPHIC")

        return GeolocationContract(
            localization=LocalizationMetadata(
                status=status,
                available_spaces=avail,
                unavailable_spaces=unavail,
                reason_code=reason_code
            ),
            pixel_convention=self.pixel_convention,
            image_geometry=image_geometry,
            coordinate_provenance=provenance,
            coordinates=CoordinatesPayload(
                image=image_coords,
                normalized_image=norm_coords,
                sonar=sonar_coords,
                geographic=geo_coords
            ),
            localization_uncertainty=ErrorEnvelopeReference(
                status="NOT_ESTIMABLE", reason="Pending F4 validation integration"
            )
        )

    def _check_sonar_capability(self, metadata: Dict[str, Any]) -> bool:
        required = ["pixel_to_range_model", "across_track_geometry", "towfish_altitude"]
        return all(k in metadata for k in required)
        
    def _check_geo_capability(self, metadata: Dict[str, Any]) -> bool:
        required = ["time_aligned_navigation", "sensor_lever_arm", "geodetic_crs", "towfish_pose"]
        has_sonar = self._check_sonar_capability(metadata)
        return has_sonar and all(k in metadata for k in required)
