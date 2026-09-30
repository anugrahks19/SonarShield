import { z } from 'zod';

const text = z.string();
const number = z.number();
const box = z.tuple([number, number, number, number]);
const flag = z.object({ code: text, severity: text }).passthrough();
const quality = z.object({
  image: z.object({ flags: z.array(flag) }).passthrough(),
  detection: z.object({ flags: z.array(flag) }).passthrough(),
  evidence: z.object({ completeness: z.object({ available: z.array(text), missing: z.array(text) }).passthrough(), flags: z.array(flag) }).passthrough(),
  localization: z.object({ flags: z.array(flag) }).passthrough(),
  metadata: z.object({ flags: z.array(flag) }).passthrough(),
}).passthrough();
const provenance = z.object({
  candidate_id: text, input_id: text, source_dataset: text, source_dataset_version: text.nullable(), image_sha256: text,
  pipeline_version: text, detector_version: text, fusion_version: text, decision_policy_version: text,
  calibration_version: text, preprocessing_version: text, coordinate_contract_version: text,
  detector_artifact_sha256: text, fusion_artifact_sha256: text, decision_policy_sha256: text,
  classification_calibration_sha256: text, localization_uncertainty_sha256: text,
  processing_timestamp: text, runtime_version: text,
}).passthrough();
const imageCoordinates = z.object({ coordinate_system: text, x_min: number, y_min: number, x_max: number, y_max: number, center_x: number, center_y: number, width_px: number, height_px: number }).passthrough();
const localization = z.object({
  metadata: z.object({ status: z.enum(['PIXEL_ONLY', 'RELATIVE_SONAR', 'GEOGRAPHIC', 'UNAVAILABLE', 'NOT_PROCESSED']), available_spaces: z.array(text), unavailable_spaces: z.array(text), reason_code: text }).passthrough(),
  pixel_convention: z.object({ origin: text, axes: text, indexing: text, bounding_box_semantics: text, reference: text }).passthrough(),
  image_geometry: z.object({ original_width_px: z.number().int(), original_height_px: z.number().int(), model_width_px: z.number().int(), model_height_px: z.number().int(), transform: text, scale_x: number, scale_y: number, pad_left_px: number, pad_top_px: number, pad_right_px: number, pad_bottom_px: number }).passthrough().nullable(),
  coordinate_provenance: z.array(z.object({ source_space: text, target_space: text, transform: text, geometry_version: text, source_dimensions: z.array(z.number().int()).nullable(), target_dimensions: z.array(z.number().int()).nullable() }).passthrough()),
  coordinates: z.object({
    image: imageCoordinates.nullable(),
    normalized_image: z.object({ center_x: number, center_y: number, width_norm: number, height_norm: number }).passthrough().nullable(),
    sonar: z.object({ coordinate_system: text, range_m: number.nullable(), along_track_m: number.nullable(), across_track_m: number.nullable() }).passthrough().nullable(),
    geographic: z.object({ coordinate_system: text, latitude: number, longitude: number, heading_deg: number.nullable() }).passthrough().nullable(),
  }).passthrough(),
}).passthrough();
const candidate = z.object({
  schema_version: text, candidate_id: text,
  detection: z.object({ class_id: z.number().int(), class_name: text, confidence: number, bbox: box, source_mode: text }).passthrough(),
  classification: z.object({
    class_id: z.number().int(), class_name: text,
    reliability: z.object({ estimated_tp_rate: number, support_count: z.number().int(), method: text, source_split: text, confidence_interval: z.object({ lower: number, upper: number }).passthrough().nullable() }).passthrough(),
    presentation: z.object({ reliability_band: text, uncertainty_level: text }).passthrough(),
  }).passthrough(),
  decision: z.object({ status: text, fusion_score: number, reason_codes: z.array(text) }).passthrough(),
  evidence: z.object({
    ai_confidence: number, bbox: box,
    geometry: z.object({ width_px: number, height_px: number, bbox_area_px: number, aspect_ratio: number }).passthrough(),
    seabed: z.object({ background_mean: number, background_std: number, local_contrast: number }).passthrough(),
    shadow: z.object({ shadow_candidate_presence: number, shadow_area_px: number, area_ratio: number, adjacency: number, mean_intensity_ratio: number }).passthrough().nullable(),
    quality: z.object({ boundary_strength: number, artifact_flags: z.record(text, z.unknown()) }).passthrough(),
  }).passthrough(),
  localization,
  localization_uncertainty: z.object({
    validation_reference: z.object({ scope: text, class_name: text, median_center_error_px: number, p90_center_error_px: number, median_normalized_center_error: number, p90_normalized_center_error: number }).passthrough().nullable(),
    error_envelope: z.object({ status: text, scope: text, method: text, envelope_px: number.nullable(), envelope_normalized: number.nullable(), reason: text.nullable() }).passthrough(),
  }).passthrough(),
  quality, provenance,
}).passthrough();

const input = z.object({ input_id: text, filename: text, sha256: text, width: z.number().int().nullable(), height: z.number().int().nullable() }).passthrough();
export const healthSchema = z.object({ status: text, schema_version: text, components: z.object({ detector: text, fusion: text, decision_policy: text, calibration: text, unknown_detector: text }).passthrough(), pipeline_version: text, uptime_seconds: z.number().int() }).passthrough();
export const analyzeSchema = z.object({ schema_version: text, analysis_id: text, status: text, input, summary: z.record(text, z.number().int()), candidates: z.array(candidate), artifacts: z.object({ visual_audit_url: text.nullable(), report_url: text.nullable() }).passthrough(), processing: z.object({ status: text, pipeline_version: text, processing_time_ms: z.number().int() }).passthrough() }).passthrough();
export const detectSchema = z.object({ schema_version: text, analysis_id: text, status: text, input, summary: z.record(text, z.number().int()), raw_candidates: z.array(z.record(text, z.unknown())), processing: z.record(text, z.unknown()) }).passthrough();
export const reportSchema = z.object({ schema_version: text, report_id: text, status: text, report_url: text.nullable(), download_url: text.nullable(), data: z.record(text, z.unknown()).nullable() }).passthrough();
