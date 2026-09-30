from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from api.f6_schema import QualityReport, ProvenanceRecord
from api.classification_schema import ClassificationPayload
from api.coordinate_schema import (
    LocalizationMetadata, PixelConvention, ImageGeometry,
    CoordinateProvenance, CoordinatesPayload,
    LocalizationValidation, ErrorEnvelopeReference
)

class DetectionPayload(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2]")
    source_mode: str = Field(..., description="GLOBAL or TILED")

class DecisionPayload(BaseModel):
    status: str = Field(..., description="CONFIRM, REVIEW, REJECT, UNKNOWN")
    fusion_score: float
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
