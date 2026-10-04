from pydantic import BaseModel, Field
from typing import Optional

class ConfidenceInterval(BaseModel):
    lower: float
    upper: float

class ReliabilityEstimate(BaseModel):
    estimated_tp_rate: float = Field(..., description="Estimated true positive rate based on CALIB split")
    support_count: int = Field(..., description="Number of examples from CALIB split supporting this bin")
    method: str = Field(default="CLASS_CONDITIONAL_EMPIRICAL_BINNING")
    source_split: str = Field(default="CALIB")
    confidence_interval: Optional[ConfidenceInterval] = None


class PresentationPolicy(BaseModel):
    reliability_band: str = Field(..., description="HIGH_RELIABILITY, MEDIUM_RELIABILITY, LOW_RELIABILITY, UNCALIBRATED")
    uncertainty_level: str = Field(..., description="LOW_UNCERTAINTY, MEDIUM_UNCERTAINTY, HIGH_UNCERTAINTY, UNKNOWN")

class ClassificationPayload(BaseModel):
    class_id: int
    class_name: str
    reliability: Optional[ReliabilityEstimate] = None
    presentation: PresentationPolicy
