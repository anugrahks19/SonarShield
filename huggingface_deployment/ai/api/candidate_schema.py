from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from ai.api.f6_schema import QualityReport, ProvenanceRecord
from ai.api.classification_schema import ClassificationPayload
from ai.api.coordinate_schema import (
    LocalizationMetadata, PixelConvention, ImageGeometry,
    CoordinateProvenance, CoordinatesPayload,
    LocalizationValidation, ErrorEnvelopeReference
)

class DetectionPayload(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    class_id: int
    class_name: str
    confidence: float = Field(ge=0, le=1)
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2]")
    source_mode: str = Field(..., description="GLOBAL or TILED")

    @field_validator('bbox')
    @classmethod
    def valid_bbox(cls, box):
        import math
        if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[0] < 0 or box[1] < 0 or box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError('Invalid detection box.')
        return box

class DecisionPayload(BaseModel):
    status: str = Field(..., description="CONFIRM, REVIEW, REJECT, UNKNOWN")
    fusion_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    reason_codes: List[str] = Field(default_factory=list)

class GeometryEvidence(BaseModel):
    width_px: float
    height_px: float
    bbox_area_px: float
    aspect_ratio: float

class SeabedEvidence(BaseModel):
    background_mean: float
    background_std: float
    local_contrast: float

class ShadowEvidence(BaseModel):
    shadow_candidate_presence: float
    shadow_area_px: float
    area_ratio: float
    adjacency: float
    mean_intensity_ratio: float

class QualityEvidence(BaseModel):
    boundary_strength: float
    artifact_flags: Dict[str, Any]

class EvidencePayload(BaseModel):
    ai_confidence: float
    bbox: List[float]
    geometry: GeometryEvidence
    seabed: SeabedEvidence
    shadow: Optional[ShadowEvidence] = None
    quality: QualityEvidence
    
class LocalizationPayload(BaseModel):
    metadata: LocalizationMetadata
    pixel_convention: PixelConvention = Field(default_factory=PixelConvention)
    image_geometry: Optional[ImageGeometry] = None
    coordinate_provenance: List[CoordinateProvenance] = Field(default_factory=list)
    coordinates: CoordinatesPayload
    physical_dimensions: Optional[Dict[str, Any]] = None

class LocalizationUncertaintyPayload(BaseModel):
    validation_reference: Optional[LocalizationValidation] = None
    error_envelope: ErrorEnvelopeReference

class Candidate(BaseModel):
    schema_version: str = Field(default="F7.0")
    candidate_id: str
    
    detection: DetectionPayload
    classification: ClassificationPayload
    decision: DecisionPayload
    
    evidence: EvidencePayload
    
    localization: LocalizationPayload
    localization_uncertainty: LocalizationUncertaintyPayload
    
    quality: QualityReport
    provenance: ProvenanceRecord
