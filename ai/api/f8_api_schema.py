from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from api.candidate_schema import Candidate

class ComponentStatus(BaseModel):
    detector: str = Field(default="READY")
    fusion: str = Field(default="READY")
    decision_policy: str = Field(default="READY")
    calibration: str = Field(default="READY")
    unknown_detector: str = Field(default="READY")

class HealthResponse(BaseModel):
    status: str = Field(default="OK", description="Service health status")
    schema_version: str = Field(default="F8.0")
    components: ComponentStatus = Field(default_factory=ComponentStatus)
    pipeline_version: str = Field(default="v1.2")
    uptime_seconds: int

class ErrorDetails(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ErrorEnvelope(BaseModel):
    schema_version: str = Field(default="F8.0")
    error: ErrorDetails
    request_id: str

class InputMetadata(BaseModel):
    input_id: str
    filename: str
    sha256: str
    width: Optional[int] = None
    height: Optional[int] = None

class DetectResponse(BaseModel):
    schema_version: str = Field(default="F8.0")
    analysis_id: str
    status: str = Field(..., description="COMPLETED, FAILED")
    
    input: InputMetadata
    
    summary: Dict[str, int] = Field(..., description="Counts of raw detection candidates")
    raw_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    
    processing: Dict[str, Any] = Field(..., description="Processing time, pipeline version, etc.")

class ArtifactsPayload(BaseModel):
    visual_audit_url: Optional[str] = None
    report_url: Optional[str] = None

class ProcessingStatus(BaseModel):
    status: str = Field(..., description="QUEUED, RUNNING, COMPLETED, FAILED")
    pipeline_version: str
    processing_time_ms: int

class AnalyzeResponse(BaseModel):
    schema_version: str = Field(default="F8.0")
    analysis_id: str
    status: str = Field(..., description="COMPLETED, ERROR")
    
    input: InputMetadata
    summary: Dict[str, int] = Field(..., description="Candidate counts")
    candidates: List[Candidate] = Field(default_factory=list)
    
    artifacts: ArtifactsPayload = Field(default_factory=ArtifactsPayload)
    processing: ProcessingStatus

class ReportRequest(BaseModel):
    analysis_ids: List[str] = Field(..., description="List of analysis IDs to include in the report")
    format: str = Field(default="JSON", description="JSON, PDF, CSV")
    include_images: bool = Field(default=False)

class ReportResponse(BaseModel):
    schema_version: str = Field(default="F8.0")
    report_id: str
    status: str = Field(..., description="GENERATED, FAILED")
    report_url: Optional[str] = None
    download_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
