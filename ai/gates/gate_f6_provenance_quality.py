import datetime
import hashlib
import uuid
from typing import Dict, Any, List

from api.f6_schema import (
    QualityReport, QualityFlag, ImageQuality, DetectionQuality,
    EvidenceQuality, EvidenceCompleteness, LocalizationQuality, MetadataQuality,
    ProvenanceRecord
)

def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file."""
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return "UNKNOWN_HASH"

class GateF6Processor:
    """
    Gate F6: Traceability Layer
    Computes quality flags and provenance for a candidate.
    """
    def __init__(self, config: Dict[str, str]):
        self.pipeline_version = config.get("pipeline_version", "v1.0.0")
        self.detector_version = config.get("detector_version", "V6-P2")
        self.fusion_version = config.get("fusion_version", "D2-v1")
        self.decision_policy_version = config.get("decision_policy_version", "E1-v1")
        self.calibration_version = config.get("calibration_version", "F5-1.0.0")
        self.preprocessing_version = config.get("preprocessing_version", "v1.0.0")
        self.coordinate_contract_version = config.get("coordinate_contract_version", "F3-1.0.0")
        self.runtime_version = config.get("runtime_version", "python-3.x")
        
        self.detector_artifact_sha256 = self._get_cached_hash(config.get("detector_artifact_path", ""))
        self.fusion_artifact_sha256 = self._get_cached_hash(config.get("fusion_artifact_path", ""))
        self.decision_policy_sha256 = self._get_cached_hash(config.get("decision_policy_path", ""))
        self.classification_calibration_sha256 = self._get_cached_hash(config.get("classification_calibration_path", ""))
        self.localization_uncertainty_sha256 = self._get_cached_hash(config.get("localization_uncertainty_path", ""))
        
    def _get_cached_hash(self, path: str) -> str:
        if not path:
            return "NO_ARTIFACT"
        return compute_sha256(path)

    def extract_provenance(self, candidate_id: str, input_id: str, image_path: str, dataset_name: str, dataset_version: str = "UNKNOWN") -> ProvenanceRecord:
        image_hash = compute_sha256(image_path)
        if image_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": # SHA-256 of empty file
            image_hash = "EMPTY_FILE_HASH"
            
        return ProvenanceRecord(
            candidate_id=candidate_id,
            input_id=input_id,
            source_dataset=dataset_name,
            source_dataset_version=dataset_version,
            image_sha256=image_hash,
            pipeline_version=self.pipeline_version,
            detector_version=self.detector_version,
            fusion_version=self.fusion_version,
            decision_policy_version=self.decision_policy_version,
            calibration_version=self.calibration_version,
            preprocessing_version=self.preprocessing_version,
            coordinate_contract_version=self.coordinate_contract_version,
            detector_artifact_sha256=self.detector_artifact_sha256,
            fusion_artifact_sha256=self.fusion_artifact_sha256,
            decision_policy_sha256=self.decision_policy_sha256,
            classification_calibration_sha256=self.classification_calibration_sha256,
            localization_uncertainty_sha256=self.localization_uncertainty_sha256,
            processing_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            runtime_version=self.runtime_version
        )

    def assess_quality(self, evidence: Dict[str, Any], localization_status: str, metadata: Dict[str, Any], image_w: int, image_h: int) -> QualityReport:
        report = QualityReport()
        
        # 1. Image Quality
        seabed = evidence.get("seabed", {})
        quality = evidence.get("quality", {})
        if seabed.get("local_contrast", 1.0) < 0.2:
            report.image.flags.append(QualityFlag(code="LOW_CONTRAST", severity="WARNING"))
        if quality.get("artifact_flags", {}).get("is_noisy", False):
            report.image.flags.append(QualityFlag(code="HIGH_NOISE", severity="WARNING"))
            
        # 2. Detection Quality
        bbox = evidence.get("bbox", [0, 0, 0, 0])
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        if bbox[0] <= 1 or bbox[1] <= 1 or bbox[2] >= image_w - 1 or bbox[3] >= image_h - 1:
            report.detection.flags.append(QualityFlag(code="EDGE_OF_IMAGE", severity="WARNING"))
        if (w * h) < 100:
            report.detection.flags.append(QualityFlag(code="SMALL_TARGET", severity="INFO"))
        if quality.get("boundary_strength", 1.0) < 0.3:
            report.detection.flags.append(QualityFlag(code="LOW_BOUNDARY_STRENGTH", severity="INFO"))

        # 3. Evidence Completeness & Quality
        available = ["AI"]
        missing = []
        
        # Check components
        if "boundary_strength" in quality: available.append("BOUNDARY")
        else: missing.append("BOUNDARY")
        
        if "local_contrast" in seabed: available.append("LOCAL_CONTRAST")
        else: missing.append("LOCAL_CONTRAST")
            
        shadow = evidence.get("shadow", {})
        if shadow.get("shadow_candidate_presence", 0.0) > 0.0:
            available.append("SHADOW")
            if shadow.get("area_ratio", 0.0) < 0.1:
                report.evidence.flags.append(QualityFlag(code="WEAK_SHADOW_SUPPORT", severity="INFO"))
        else:
            missing.append("SHADOW")
            report.evidence.flags.append(QualityFlag(code="MISSING_SHADOW_SUPPORT", severity="INFO"))
            
        report.evidence.completeness.available = available
        report.evidence.completeness.missing = missing
        
        # 4. Localization Quality
        if localization_status == "PIXEL_ONLY":
            report.localization.flags.append(QualityFlag(code="PIXEL_ONLY", severity="WARNING"))
        elif localization_status == "RELATIVE_SONAR":
            report.localization.flags.append(QualityFlag(code="NO_NAVIGATION_METADATA", severity="INFO"))
        elif localization_status in ["UNAVAILABLE", "NOT_PROCESSED"]:
            report.localization.flags.append(QualityFlag(code="LOCALIZATION_UNAVAILABLE", severity="ERROR"))
            
        # 5. Metadata Quality
        if not metadata.get("time_aligned_navigation"):
            report.metadata.flags.append(QualityFlag(code="MISSING_NAVIGATION", severity="WARNING"))
        if not metadata.get("sensor_lever_arm"):
            report.metadata.flags.append(QualityFlag(code="MISSING_SENSOR_POSE", severity="WARNING"))
        if not metadata.get("geodetic_crs"):
            report.metadata.flags.append(QualityFlag(code="MISSING_CRS", severity="INFO"))

        return report

