from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class LocalizationStatus(str, Enum):
    PIXEL_ONLY = "PIXEL_ONLY"
    RELATIVE_SONAR = "RELATIVE_SONAR"
    GEOGRAPHIC = "GEOGRAPHIC"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_PROCESSED = "NOT_PROCESSED"

class LocalizationMetadata(BaseModel):
    status: LocalizationStatus
    available_spaces: List[str]
    unavailable_spaces: List[str]
    reason_code: str

class ImageGeometry(BaseModel):
    original_width_px: int
    original_height_px: int
    model_width_px: int
    model_height_px: int
    transform: str = Field(default="LETTERBOX", description="Transform applied before model inference")
    scale_x: float
    scale_y: float
    pad_left_px: float
    pad_top_px: float
    pad_right_px: float
    pad_bottom_px: float

class PixelConvention(BaseModel):
    origin: str = "top-left"
    axes: str = "x rightward, y downward"
    indexing: str = "zero-based continuous"
    bounding_box_semantics: str = "[x_min, y_min, x_max, y_max), max exclusive"
    reference: str = "pixel center of (i,j) is (j + 0.5, i + 0.5)"

class CoordinateProvenance(BaseModel):
    source_space: str
    target_space: str
    transform: str
    geometry_version: str = "1.0"
    source_dimensions: Optional[List[int]] = None
    target_dimensions: Optional[List[int]] = None

class ImageCoordinates(BaseModel):
    coordinate_system: str = Field(default="IMAGE_PIXEL", description="Coordinate space identifier")
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    center_x: float
    center_y: float
    width_px: float
    height_px: float

class NormalizedImageCoordinates(BaseModel):
    center_x: float
    center_y: float
    width_norm: float
    height_norm: float

class SonarCoordinates(BaseModel):
    coordinate_system: str = Field(default="SONAR_RELATIVE", description="Coordinate space identifier")
    range_m: Optional[float] = None
    along_track_m: Optional[float] = None
    across_track_m: Optional[float] = None

class GeographicCoordinates(BaseModel):
    coordinate_system: str = Field(default="WGS84", description="Coordinate reference system")
    latitude: float
    longitude: float
    heading_deg: Optional[float] = None

class LocalizationValidation(BaseModel):
    scope: str = Field(default="CLASS_LEVEL")
    class_name: str
    median_center_error_px: float
    p90_center_error_px: float
    median_normalized_center_error: float
    p90_normalized_center_error: float

class ErrorEnvelopeReference(BaseModel):
    status: str = Field(..., description="CLASS_CONDITIONAL_ESTIMATE, NOT_ESTIMABLE")
    scope: str = Field(default="CLASS_CONDITIONAL")
    method: str = Field(default="CALIB_DERIVED_P90_ENVELOPE")
    envelope_px: Optional[float] = None
    envelope_normalized: Optional[float] = None
    reason: Optional[str] = None

class CoordinatesPayload(BaseModel):
    image: Optional[ImageCoordinates] = None
    normalized_image: Optional[NormalizedImageCoordinates] = None
    sonar: Optional[SonarCoordinates] = None
    geographic: Optional[GeographicCoordinates] = None

class GeolocationContract(BaseModel):
    localization: LocalizationMetadata
    pixel_convention: PixelConvention = Field(default_factory=PixelConvention)
    image_geometry: Optional[ImageGeometry] = None
    coordinate_provenance: List[CoordinateProvenance] = Field(default_factory=list)
    coordinates: CoordinatesPayload
    localization_validation: Optional[LocalizationValidation] = None
    localization_uncertainty: ErrorEnvelopeReference


