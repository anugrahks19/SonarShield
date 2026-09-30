import sys
from pathlib import Path
import json
import uuid
import time
import numpy as np
import cv2
import gradio as gr
import spaces
import datetime

# Add the 'ai' directory to the Python path so the internal imports work
sys.path.append(str(Path(__file__).parent / "ai"))
from ai.api.gate_f8_api_server import (
    detector, fusion_pipeline, fusion_features, decision_engine,
    extract_all_evidence,
    AnalyzeResponse, InputMetadata, ProcessingStatus,
    DetectionPayload, EvidencePayload, GeometryEvidence, SeabedEvidence,
    ShadowEvidence, QualityEvidence, ClassificationPayload, ReliabilityEstimate,
    PresentationPolicy, DecisionPayload, LocalizationPayload, LocalizationMetadata,
    PixelConvention, CoordinatesPayload, ImageCoordinates, LocalizationUncertaintyPayload,
    LocalizationValidation, ErrorEnvelopeReference, ProvenanceRecord, QualityReport,
    ImageQuality, DetectionQuality, EvidenceQuality, EvidenceCompleteness,
    LocalizationQuality, MetadataQuality, Candidate, ArtifactsPayload
)

@spaces.GPU
def analyze_image_gradio(image_filepath, run_tiled_auxiliary=True):
    if image_filepath is None:
        return '{"error": "No image provided"}'
        
    start_time = time.time()
    
    # Read the image
    image = cv2.imread(image_filepath)
    if image is None:
        return '{"error": "Invalid image format"}'
        
    img_h, img_w = image.shape[:2]
    img_sha256 = "dummy_sha" 
    
    input_meta = InputMetadata(
        input_id=f"IMG-{uuid.uuid4().hex[:8]}",
        filename=Path(image_filepath).name,
        sha256=img_sha256,
        width=img_w,
        height=img_h
    )
    analysis_id = f"ANL-{uuid.uuid4().hex[:8]}"
    
    # Gate B - Run detector (this utilizes the GPU)
    global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
    for p in global_preds: p['source_mode'] = 'GLOBAL'
        
    tiled_preds = []
    if run_tiled_auxiliary:
        tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
        for p in tiled_preds: p['source_mode'] = 'TILED'
            
    all_candidates_raw = global_preds
    for tp in tiled_preds:
        tx1, ty1, tx2, ty2 = tp['bbox']
        tcx, tcy = (tx1 + tx2) / 2, (ty1 + ty2) / 2
        is_new = True
        for gp in global_preds:
            gx1, gy1, gx2, gy2 = gp['bbox']
            gcx, gcy = (gx1 + gx2) / 2, (gy1 + gy2) / 2
            if ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5 < 50:
                is_new = False
                break
        if is_new:
            all_candidates_raw.append(tp)
            
    final_candidates = []
    status_counts = {"CONFIRM": 0, "REVIEW": 0, "REJECT": 0, "UNKNOWN": 0}
    
    for cand_idx, raw_cand in enumerate(all_candidates_raw):
        cand_id = f"CAND-{uuid.uuid4().hex[:8]}"
        ev = extract_all_evidence(image, raw_cand)
        
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
        fusion_probs = fusion_pipeline.predict_proba(X_arr)
        fusion_score = float(fusion_probs[0][1])
        std_features = fusion_pipeline.named_steps['scaler'].transform(X_arr)
        
        decision_payload = decision_engine.evaluate_candidate(ev, std_features, fusion_score)
        decision_status = decision_payload["decision"]
        if decision_status not in status_counts: status_counts[decision_status] = 0
        status_counts[decision_status] += 1
        
        class_map = {0: "Crab Pot", 1: "Wreck", 2: "Mine", 3: "Pipeline", 4: "Ghost Net"}
        c_name = class_map.get(raw_cand["class"], "Unknown")
        
        detection_p = DetectionPayload(class_id=raw_cand["class"], class_name=c_name, confidence=raw_cand["detector_confidence"], bbox=raw_cand["bbox"], source_mode=raw_cand["source_mode"])
        evidence_p = EvidencePayload(
            ai_confidence=ev["confidence"], bbox=ev["bbox"], geometry=GeometryEvidence(**ev["object"]),
            seabed=SeabedEvidence(background_mean=ev["seabed"]["mean_intensity"], background_std=ev["seabed"]["std_intensity"], local_contrast=ev["seabed"]["local_contrast"]),
            shadow=ShadowEvidence(shadow_area_px=ev["shadow"]["area_ratio"] * ev["object"]["bbox_area_px"], **ev["shadow"]),
            quality=QualityEvidence(boundary_strength=ev["quality"]["boundary_strength"], artifact_flags=ev["quality"]["artifact_flags"])
        )
        class_p = ClassificationPayload(class_id=raw_cand["class"], class_name=c_name, reliability=ReliabilityEstimate(estimated_tp_rate=0.85, support_count=100), presentation=PresentationPolicy(reliability_band="MODERATE", uncertainty_level="LOW_UNCERTAINTY"))
        dec_p = DecisionPayload(status=decision_status, fusion_score=fusion_score, reason_codes=decision_payload["reason_codes"])
        
        x1, y1, x2, y2 = ev["bbox"]
        loc_p = LocalizationPayload(
            metadata=LocalizationMetadata(status="PIXEL_ONLY", available_spaces=["IMAGE_PIXEL"], unavailable_spaces=["SONAR_RELATIVE", "GEOGRAPHIC"], reason_code="NO_SONAR_NAV_METADATA"),
            pixel_convention=PixelConvention(), coordinate_provenance=[],
            coordinates=CoordinatesPayload(image=ImageCoordinates(x_min=x1, y_min=y1, x_max=x2, y_max=y2, center_x=(x1+x2)/2, center_y=(y1+y2)/2, width_px=x2-x1, height_px=y2-y1))
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
            image=ImageQuality(flags=[]), detection=DetectionQuality(flags=[]),
            evidence=EvidenceQuality(completeness=EvidenceCompleteness(available=[], missing=[]), flags=[]),
            localization=LocalizationQuality(flags=[]), metadata=MetadataQuality(flags=[])
        )
        
        cand = Candidate(
            candidate_id=cand_id, detection=detection_p, classification=class_p, decision=dec_p,
            evidence=evidence_p, localization=loc_p, localization_uncertainty=loc_unc_p,
            quality=qual_p, provenance=prov_p
        )
        final_candidates.append(cand)
        
    summary_dict = {
        "candidate_count": len(final_candidates),
        "confirmed_count": status_counts.get("CONFIRM", 0),
        "review_count": status_counts.get("REVIEW", 0),
        "rejected_count": status_counts.get("REJECT", 0),
        "unknown_count": status_counts.get("UNKNOWN", 0)
    }
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    resp = AnalyzeResponse(
        analysis_id=analysis_id,
        status="COMPLETED",
        input=input_meta,
        summary=summary_dict,
        candidates=final_candidates,
        artifacts=ArtifactsPayload(visual_audit_url=None),
        processing=ProcessingStatus(status="COMPLETED", pipeline_version="v1.2", processing_time_ms=elapsed_ms)
    )
    
    return resp.model_dump_json()


demo = gr.Interface(
    fn=analyze_image_gradio,
    inputs=[
        gr.Image(type="filepath", label="Sonar Image"), 
        gr.Checkbox(value=True, label="Run Tiled Auxiliary")
    ],
    outputs=gr.JSON(label="Analysis Results"),
    title="🚀 SONAR-SHIELD API",
    description="This Gradio UI serves as the official REST API endpoint for the React frontend."
)

if __name__ == "__main__":
    demo.launch()
