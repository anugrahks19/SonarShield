// F7 declares status and severity as strings; known values inform presentation only.
export type DecisionStatus = 'CONFIRM' | 'REVIEW' | 'REJECT' | 'UNKNOWN' | (string & {});
export type QualityFlag = { code: string; severity: string };
export type QualityReport = {
  image: { flags: QualityFlag[] }; detection: { flags: QualityFlag[] };
  evidence: { completeness: { available: string[]; missing: string[] }; flags: QualityFlag[] };
  localization: { flags: QualityFlag[] }; metadata: { flags: QualityFlag[] };
};
export type ProvenanceRecord = {
  candidate_id: string; input_id: string; source_dataset: string; source_dataset_version: string | null;
  image_sha256: string; pipeline_version: string; detector_version: string; fusion_version: string;
  decision_policy_version: string; calibration_version: string; preprocessing_version: string;
  coordinate_contract_version: string; detector_artifact_sha256: string; fusion_artifact_sha256: string;
  decision_policy_sha256: string | null; classification_calibration_sha256: string | null;
  localization_uncertainty_sha256: string | null; processing_timestamp: string; runtime_version: string;
};
export type Candidate = {
  schema_version: string; candidate_id: string;
  detection: { class_id: number; class_name: string; confidence: number; bbox: number[]; source_mode: string };
  classification: { class_id: number; class_name: string; reliability: { estimated_tp_rate: number; support_count: number; method: string; source_split: string; confidence_interval: { lower: number; upper: number } | null } | null; presentation: { reliability_band: string; uncertainty_level: string } };
  decision: { status: DecisionStatus; fusion_score: number; reason_codes: string[] };
  evidence: { ai_confidence: number; bbox: number[]; geometry: { width_px: number; height_px: number; bbox_area_px: number; aspect_ratio: number }; seabed: { background_mean: number; background_std: number; local_contrast: number }; shadow: { shadow_candidate_presence: number; shadow_area_px: number; area_ratio: number; adjacency: number; mean_intensity_ratio: number } | null; quality: { boundary_strength: number; artifact_flags: Record<string, unknown> } };
  localization: { physical_dimensions?: { width_m: number; height_m: number; method: string; status: string } | null; metadata: { status: 'PIXEL_ONLY' | 'RELATIVE_SONAR' | 'GEOGRAPHIC' | 'UNAVAILABLE' | 'NOT_PROCESSED'; available_spaces: string[]; unavailable_spaces: string[]; reason_code: string }; pixel_convention: { origin: string; axes: string; indexing: string; bounding_box_semantics: string; reference: string }; image_geometry: { original_width_px: number; original_height_px: number; model_width_px: number; model_height_px: number; transform: string; scale_x: number; scale_y: number; pad_left_px: number; pad_top_px: number; pad_right_px: number; pad_bottom_px: number } | null; coordinate_provenance: { source_space: string; target_space: string; transform: string; geometry_version: string; source_dimensions: number[] | null; target_dimensions: number[] | null }[]; coordinates: { image: { coordinate_system: string; center_x: number; center_y: number; x_min: number; y_min: number; x_max: number; y_max: number; width_px: number; height_px: number } | null; normalized_image: { center_x: number; center_y: number; width_norm: number; height_norm: number } | null; sonar: { coordinate_system: string; range_m: number | null; along_track_m: number | null; across_track_m: number | null } | null; geographic: { coordinate_system: string; latitude: number; longitude: number; heading_deg: number | null } | null } };
  localization_uncertainty: { validation_reference: { scope: string; class_name: string; median_center_error_px: number; p90_center_error_px: number; median_normalized_center_error: number; p90_normalized_center_error: number } | null; error_envelope: { status: string; scope: string; method: string; envelope_px: number | null; envelope_normalized: number | null; reason: string | null } };
  quality: QualityReport;
  provenance: ProvenanceRecord;
};
export type AnalyzeResponse = {
  schema_version: string; analysis_id: string; status: string;
  input: { input_id: string; filename: string; sha256: string; width: number | null; height: number | null };
  summary: Record<string, number>; candidates: Candidate[];
  artifacts: { visual_audit_url: string | null; report_url: string | null };
  processing: { status: string; pipeline_version: string; processing_time_ms: number };
};
export type DetectResponse = {
  schema_version: string; analysis_id: string; status: string;
  input: AnalyzeResponse['input']; summary: Record<string, number>;
  raw_candidates: Record<string, unknown>[]; processing: Record<string, unknown>;
};
export type ReportRequest = { analysis_ids: string[]; format?: string; include_images?: boolean };
export type ReportResponse = { schema_version: string; report_id: string; status: string; report_url: string | null; download_url: string | null; data: Record<string, unknown> | null };
export type HealthResponse = { status: string; schema_version: string; components: Record<string, string>; pipeline_version: string; uptime_seconds: number | null };
export type ApiError = { code: string; message: string; details?: Record<string, unknown> };
