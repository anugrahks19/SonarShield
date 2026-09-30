from typing import List, Optional
from pydantic import BaseModel, Field

class QualityFlag(BaseModel):
    code: str = Field(..., description="Machine-readable code like LOW_CONTRAST or PIXEL_ONLY")
    severity: str = Field(..., description="INFO, WARNING, or ERROR")

class ImageQuality(BaseModel):
    flags: List[QualityFlag] = Field(default_factory=list)

class DetectionQuality(BaseModel):
    flags: List[QualityFlag] = Field(default_factory=list)

class EvidenceCompleteness(BaseModel):
    available: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)

class EvidenceQuality(BaseModel):
    completeness: EvidenceCompleteness
    flags: List[QualityFlag] = Field(default_factory=list)

class LocalizationQuality(BaseModel):
    flags: List[QualityFlag] = Field(default_factory=list)

class MetadataQuality(BaseModel):
    flags: List[QualityFlag] = Field(default_factory=list)

class QualityReport(BaseModel):
    image: ImageQuality = Field(default_factory=ImageQuality)
    detection: DetectionQuality = Field(default_factory=DetectionQuality)
    evidence: EvidenceQuality = Field(default_factory=lambda: EvidenceQuality(completeness=EvidenceCompleteness()))
    localization: LocalizationQuality = Field(default_factory=LocalizationQuality)
    metadata: MetadataQuality = Field(default_factory=MetadataQuality)

class ProvenanceRecord(BaseModel):
    candidate_id: str
    input_id: str
    source_dataset: str
    source_dataset_version: Optional[str] = None
    image_sha256: str
    
    pipeline_version: str
    detector_version: str
    fusion_version: str
    decision_policy_version: str
    calibration_version: str
    preprocessing_version: str
    coordinate_contract_version: str
    
    detector_artifact_sha256: str
    fusion_artifact_sha256: str
    decision_policy_sha256: str
    classification_calibration_sha256: str
    localization_uncertainty_sha256: str
    
    processing_timestamp: str
    runtime_version: str
