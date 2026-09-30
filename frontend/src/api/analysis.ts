import type { AnalyzeResponse, DetectResponse } from '../types';
import { analyzeSchema } from './schema';
import { Client } from '@gradio/client';
import { AnalysisError } from './errors';

export async function analyzeImage(file: File, _signal?: AbortSignal): Promise<AnalyzeResponse> {
  try {
    // Connect directly to the Hugging Face GPU space
    const client = await Client.connect("mrintrovert19/sonar-shield-api");
    
    // Send the image and "true" for run_tiled_auxiliary
    const result = await client.predict("/predict", [
      file, 
      true
    ]);
    
    // The backend returns a JSON string as the first data output
    const jsonString = (result.data as unknown[])[0] as string;
    const payload = JSON.parse(jsonString);
    
    // Make sure the API didn't return a graceful error inside the JSON
    if (payload.error) {
      throw new Error(payload.error);
    }
    
    return analyzeSchema.parse(payload);
  } catch (err: any) {
    throw new AnalysisError('API_OFFLINE', err.message || 'Failed to analyze image via Hugging Face.');
  }
}

export async function detectImage(file: File, _signal?: AbortSignal): Promise<DetectResponse> {
  // We can just use analyzeImage since our new backend does everything in one pass!
  const analysis = await analyzeImage(file);
  return {
    schema_version: "F7.0",
    analysis_id: analysis.analysis_id,
    status: analysis.status,
    input: analysis.input,
    summary: { raw_candidate_count: analysis.summary.candidate_count },
    raw_candidates: [],
    processing: analysis.processing
  };
}
