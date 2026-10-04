from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
import math,re
from ai.schemas.class_map import CLASS_ID_TO_DISPLAY_NAME
from ai.api.candidate_schema import Candidate

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

    @model_validator(mode='after')
    def corrected_contract(self):
        if self.schema_version!='F8.1':return self
        if self.status!='COMPLETED' or self.processing.status!='COMPLETED' or self.processing.processing_time_ms<0:raise ValueError('Invalid completed processing contract.')
        if not self.input.width or not self.input.height or min(self.input.width,self.input.height)<1 or not re.fullmatch('[a-f0-9]{64}',self.input.sha256):raise ValueError('Invalid input identity.')
        if self.input.width*self.input.height>16_000_000:raise ValueError('Input dimensions exceed limit.')
        counts={'CONFIRM':0,'REVIEW':0,'REJECT':0,'UNKNOWN':0};ids=set()
        for candidate in self.candidates:
            if candidate.candidate_id in ids:raise ValueError('Duplicate candidate identity.')
            ids.add(candidate.candidate_id);d=candidate.detection;c=candidate.classification;p=candidate.provenance
            if CLASS_ID_TO_DISPLAY_NAME.get(d.class_id)!=d.class_name or (c.class_id,c.class_name)!=(d.class_id,d.class_name):raise ValueError('Class identity mismatch.')
            if d.bbox[2]>self.input.width or d.bbox[3]>self.input.height:raise ValueError('Box outside input.')
            if candidate.decision.status not in counts:raise ValueError('Invalid decision status.')
            counts[candidate.decision.status]+=1
            if (p.input_id,p.image_sha256,p.candidate_id)!=(self.input.input_id,self.input.sha256,candidate.candidate_id):raise ValueError('Provenance identity mismatch.')
            for digest in [p.detector_artifact_sha256,p.fusion_artifact_sha256]:
                if not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('Invalid artifact digest.')
            coordinates=candidate.localization.coordinates;geo=coordinates.geographic
            if (candidate.localization.metadata.status=='GEOGRAPHIC')!=(geo is not None):raise ValueError('Geographic status disagrees with coordinates.')
            if geo and (not math.isfinite(geo.latitude) or not math.isfinite(geo.longitude) or abs(geo.latitude)>90 or abs(geo.longitude)>180 or geo.coordinate_system!='WGS84'):raise ValueError('Invalid geographic position.')
        expected={'candidate_count':len(self.candidates),'confirmed_count':counts['CONFIRM'],'review_count':counts['REVIEW'],'rejected_count':counts['REJECT'],'unknown_count':counts['UNKNOWN']}
        if any(self.summary.get(k)!=v for k,v in expected.items()):raise ValueError('Summary disagrees with candidates.')
        return self

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
