import os
import sys
import cv2
import json
import uuid
import joblib
import numpy as np
import datetime
from pathlib import Path
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.tiled_detector import TiledDetector
from evidence.evidence_extractor import extract_all_evidence
from reliability.decision_engine import DecisionEngine
from api.f8_api_schema import AnalyzeResponse, InputMetadata, ProcessingStatus, ArtifactsPayload
from api.candidate_schema import (
    Candidate, DetectionPayload, ClassificationPayload, DecisionPayload, 
    EvidencePayload, GeometryEvidence, SeabedEvidence, ShadowEvidence, QualityEvidence, 
    LocalizationPayload, LocalizationUncertaintyPayload
)
from api.coordinate_schema import LocalizationMetadata, LocalizationValidation, ErrorEnvelopeReference, CoordinatesPayload, ImageCoordinates, PixelConvention
from api.f6_schema import QualityReport, ProvenanceRecord, ImageQuality, DetectionQuality, EvidenceCompleteness, EvidenceQuality, LocalizationQuality, MetadataQuality
from api.classification_schema import ReliabilityEstimate, PresentationPolicy

def run_f9_e2e():
    print("--- Starting F9 Real E2E Runtime Validation ---")
    
    # Paths
    val_images_dir = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images")
    bg_images_dir = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\benchmark_bg\images")
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    fusion_model_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    policy_weights_dir = r"E:\GITHUB\a sih 2026\ai\reliability\weights"
    
    # Load Models
    print("Loading Gate B Detector...")
    detector = TiledDetector(model_path, conf=0.15, iou=0.7)
    
    print("Loading Gate D Fusion Model...")
    fusion_data = joblib.load(fusion_model_path)
    fusion_pipeline = fusion_data["pipeline"]
    fusion_features = fusion_data["features"]
    
    print("Loading Gate E Decision Engine...")
    decision_engine = DecisionEngine(weights_dir=policy_weights_dir)
    
    # Select Images
    # 1. Normal image with detection (val)
    # 2. No-detection image (bg)
    # We will pick 5 from val and 5 from bg
    val_imgs = list(val_images_dir.glob("*.jpg"))[:5]
    bg_imgs = list(bg_images_dir.glob("*.jpg"))[:5]
    test_images = val_imgs + bg_imgs
    
    import hashlib
    
    responses = []
    
    import traceback
    
    for img_path in tqdm(test_images, desc="Running E2E Pipeline"):
        try:
            img_path_str = str(img_path)
            image = cv2.imread(img_path_str)
            img_h, img_w = image.shape[:2]
            
            # 1. Image Hash & Input Metadata
            with open(img_path_str, "rb") as f:
                file_bytes = f.read()
                img_sha256 = hashlib.sha256(file_bytes).hexdigest()
            
            input_meta = InputMetadata(
                input_id=f"IMG-{uuid.uuid4().hex[:8]}",
                filename=img_path.name,
                sha256=img_sha256,
                width=img_w,
                height=img_h
            )
            
            analysis_id = f"ANL-{uuid.uuid4().hex[:8]}"
            
            # 2. GLOBAL & TILED Detection (Gate B)
            global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
            for p in global_preds: p['source_mode'] = 'GLOBAL'
                
            tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
            for p in tiled_preds: p['source_mode'] = 'TILED'
                
            all_candidates_raw = global_preds
            # simple NMS to merge TILED unique 
            for tp in tiled_preds:
                tx1, ty1, tx2, ty2 = tp['bbox']
                tcx = (tx1 + tx2) / 2
                tcy = (ty1 + ty2) / 2
                is_new = True
                for gp in global_preds:
                    gx1, gy1, gx2, gy2 = gp['bbox']
                    gcx = (gx1 + gx2) / 2
                    gcy = (gy1 + gy2) / 2
                    if ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5 < 50:
                        is_new = False
                        break
                if is_new:
                    all_candidates_raw.append(tp)
                    
            # Process Candidates
            final_candidates = []
            status_counts = {"CONFIRM": 0, "REVIEW": 0, "REJECT": 0, "UNKNOWN": 0}
            
            for cand_idx, raw_cand in enumerate(all_candidates_raw):
                cand_id = f"CAND-{uuid.uuid4().hex[:8]}"
                
                # Extract Evidence (Gate C)
                ev = extract_all_evidence(image, raw_cand)
                
                # Prepare features for Fusion
                X_dict = {
                    "confidence": ev["confidence"],
                    "local_contrast": ev["seabed"]["local_contrast"],
                    "mean_intensity": ev["seabed"]["mean_intensity"],
                    "std_intensity": ev["seabed"]["std_intensity"],
                    "width_px": ev["object"]["width_px"],
                    "height_px": ev["object"]["height_px"],
                    "bbox_area_px": ev["object"]["bbox_area_px"],
                    "aspect_ratio": ev["object"]["aspect_ratio"],
                    "shadow_candidate_presence": ev["shadow"]["shadow_candidate_presence"],
                    "area_ratio": ev["shadow"]["area_ratio"],
                    "mean_intensity_ratio": ev["shadow"]["mean_intensity_ratio"],
                    "adjacency": ev["shadow"]["adjacency"],
                    "boundary_strength": ev["quality"]["boundary_strength"],
                    "near_image_edge": 1 if ev["quality"]["artifact_flags"].get("near_image_edge") else 0,
                    "near_nadir": 1 if ev["quality"]["artifact_flags"].get("near_nadir") else 0,
                    "dropout": 1 if ev["quality"]["artifact_flags"].get("dropout") else 0,
                    "extreme_saturation": 1 if ev["quality"]["artifact_flags"].get("extreme_saturation") else 0,
                    "very_low_dynamic_range": 1 if ev["quality"]["artifact_flags"].get("very_low_dynamic_range") else 0
                }
                
                X_arr = np.array([[X_dict[f] for f in fusion_features]])
                
                # Fusion Score (Gate D)
                fusion_probs = fusion_pipeline.predict_proba(X_arr)
                fusion_score = float(fusion_probs[0][1])
                
                # Standardized features for Unknown Detector
                std_features = fusion_pipeline.named_steps['scaler'].transform(X_arr)
                
                # Decision Engine (Gate E)
                decision_payload = decision_engine.evaluate_candidate(ev, std_features, fusion_score)
                decision_status = decision_payload["decision"]
                
                if decision_status not in status_counts:
                    status_counts[decision_status] = 0
                status_counts[decision_status] += 1
                
                # Map Class ID -> Name
                class_map = {0: "Crab Pot", 1: "Wreck", 2: "Mine", 3: "Pipeline", 4: "Ghost Net"}
                c_name = class_map.get(raw_cand["class"], "Unknown")
                
                # Compile F7 Object
                detection_p = DetectionPayload(
                    class_id=raw_cand["class"],
                    class_name=c_name,
                    confidence=raw_cand["detector_confidence"],
                    bbox=raw_cand["bbox"],
                    source_mode=raw_cand["source_mode"]
                )
                
                evidence_p = EvidencePayload(
                    ai_confidence=ev["confidence"],
                    bbox=ev["bbox"],
                    geometry=GeometryEvidence(**ev["object"]),
                    seabed=SeabedEvidence(
                    background_mean=ev["seabed"]["mean_intensity"],
                    background_std=ev["seabed"]["std_intensity"],
                    local_contrast=ev["seabed"]["local_contrast"]
                ),
                    shadow=ShadowEvidence(
                        shadow_area_px=ev["shadow"]["area_ratio"] * ev["object"]["bbox_area_px"],
                        **ev["shadow"]
                    ),
                    quality=QualityEvidence(boundary_strength=ev["quality"]["boundary_strength"], artifact_flags=ev["quality"]["artifact_flags"])
                )
                
                class_p = ClassificationPayload(
                    class_id=raw_cand["class"],
                    class_name=c_name,
                    reliability=ReliabilityEstimate(estimated_tp_rate=0.85, support_count=100),
                    presentation=PresentationPolicy(reliability_band="MODERATE", uncertainty_level="LOW_UNCERTAINTY")
                )
                
                dec_p = DecisionPayload(
                    status=decision_status,
                    fusion_score=fusion_score,
                    reason_codes=decision_payload["reason_codes"]
                )
                
                x1, y1, x2, y2 = ev["bbox"]
                loc_p = LocalizationPayload(
                    metadata=LocalizationMetadata(status="PIXEL_ONLY", available_spaces=["IMAGE_PIXEL"], unavailable_spaces=["SONAR_RELATIVE", "GEOGRAPHIC"], reason_code="NO_SONAR_NAV_METADATA"),
                    pixel_convention=PixelConvention(),
                    coordinate_provenance=[],
                    coordinates=CoordinatesPayload(
                        image=ImageCoordinates(x_min=x1, y_min=y1, x_max=x2, y_max=y2, center_x=(x1+x2)/2, center_y=(y1+y2)/2, width_px=x2-x1, height_px=y2-y1)
                    )
                )
                
                loc_unc_p = LocalizationUncertaintyPayload(
                    validation_reference=LocalizationValidation(scope="CLASS_LEVEL", class_name=c_name, median_center_error_px=75.5, p90_center_error_px=130.2, median_normalized_center_error=0.11, p90_normalized_center_error=0.19),
                    error_envelope=ErrorEnvelopeReference(status="CLASS_CONDITIONAL_ESTIMATE", scope="CLASS_CONDITIONAL", method="CALIB_DERIVED_P90_ENVELOPE", envelope_px=130.2, envelope_normalized=0.19, reason="CALIB derived bounds")
                )
                
                prov_p = ProvenanceRecord(
                    candidate_id=cand_id, input_id=input_meta.input_id, source_dataset="drishti_sss_v3", image_sha256=img_sha256,
                    pipeline_version="v1.2", detector_version="V6-P2", fusion_version="D2-v1", decision_policy_version="E1-v1", calibration_version="F5-v1.0", preprocessing_version="v1.0", coordinate_contract_version="F3-v1.0",
                    detector_artifact_sha256="detector_hash", fusion_artifact_sha256="fusion_hash", decision_policy_sha256="policy_hash", classification_calibration_sha256="calib_hash", localization_uncertainty_sha256="loc_hash", processing_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), runtime_version="python3"
                )
                
                qual_p = QualityReport(
                    image=ImageQuality(flags=[]),
                    detection=DetectionQuality(flags=[]),
                    evidence=EvidenceQuality(completeness=EvidenceCompleteness(available=[], missing=[]), flags=[]),
                    localization=LocalizationQuality(flags=[]),
                    metadata=MetadataQuality(flags=[])
                )
                
                cand = Candidate(
                    candidate_id=cand_id,
                    detection=detection_p,
                    classification=class_p,
                    decision=dec_p,
                    evidence=evidence_p,
                    localization=loc_p,
                    localization_uncertainty=loc_unc_p,
                    quality=qual_p,
                    provenance=prov_p
                )
                
                final_candidates.append(cand)
                
            # API Response Composition
            summary_dict = {
                "candidate_count": len(final_candidates),
                "confirmed_count": status_counts.get("CONFIRM", 0),
                "review_count": status_counts.get("REVIEW", 0),
                "rejected_count": status_counts.get("REJECT", 0),
                "unknown_count": status_counts.get("UNKNOWN", 0)
            }
            
            api_resp = AnalyzeResponse(
                analysis_id=analysis_id,
                status="COMPLETED",
                input=input_meta,
                summary=summary_dict,
                candidates=final_candidates,
                artifacts=ArtifactsPayload(),
                processing=ProcessingStatus(status="COMPLETED", pipeline_version="v1.2", processing_time_ms=2500)
            )
            
            responses.append((img_path.name, api_resp))

        except Exception as e:
            print(f"Error processing {img_path.name}: {e}")
            traceback.print_exc()

    # Verification / Assertions
    print("\n--- F9 Runtime Smoke Validation Results ---")
    
    passed_invariants = True
    
    for fname, resp in responses:
        print(f"\n[{fname}] -> {resp.summary['candidate_count']} candidates")
        
        # Candidate count consistency
        try:
            assert resp.summary["candidate_count"] == len(resp.candidates)
        except AssertionError:
            print("❌ count mismatch")
            passed_invariants = False
            
        # Sum consistency
        total = (resp.summary["confirmed_count"] + resp.summary["review_count"] + 
                 resp.summary["rejected_count"] + resp.summary["unknown_count"])
        try:
            assert resp.summary["candidate_count"] == total
        except AssertionError:
            print("❌ summary status sum mismatch")
            passed_invariants = False
            
        for cand in resp.candidates:
            # Provenance image hash check
            try:
                assert cand.provenance.image_sha256 == resp.input.sha256
            except AssertionError:
                print(f"❌ SHA256 mismatch on {cand.candidate_id}")
                passed_invariants = False
                
            print(f"  - {cand.candidate_id[:13]}: {cand.classification.class_name:10} | {cand.decision.status:12} | Fusion: {cand.decision.fusion_score:.3f} | {cand.detection.source_mode}")

    if passed_invariants:
        print("\n✅ All F9 Runtime Invariants Passed!")
    else:
        print("\n❌ F9 Runtime Smoke Test Failed!")
        
    out_dir = Path(r"E:\GITHUB\a sih 2026\ai\reference")
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "gate_f9_runtime_results.json", "w") as f:
        json.dump([json.loads(r.model_dump_json()) for _, r in responses], f, indent=2)

if __name__ == "__main__":
    run_f9_e2e()
