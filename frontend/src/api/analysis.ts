import { Client, handle_file } from '@gradio/client';
import type { AnalyzeResponse, DetectResponse } from '../types';
import { analyzeSchema } from './schema';
import { AnalysisError } from './errors';
import { gradioSpaceId } from '../config/env';

const analysisEndpoint = '/analyze_image_gradio';

export async function analyzeImage(file: File, signal?: AbortSignal): Promise<AnalyzeResponse> {
  if (signal?.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.');
  let client: Client | undefined;
  try {
    client = await Client.connect(gradioSpaceId);
    if (signal?.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.');
    const response = await client.predict(analysisEndpoint, {
      image_filepath: handle_file(file),
      run_tiled_auxiliary: true,
    });
    if (signal?.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.');
    const data: unknown = response.data;
    const output: unknown = Array.isArray(data) ? data[0] : undefined;
    const payload: unknown = typeof output === 'string' ? JSON.parse(output) : output;
    if (payload && typeof payload === 'object' && 'error' in payload) {
      throw new AnalysisError('ANALYSIS_FAILED', String(payload.error));
    }
    const parsed = analyzeSchema.safeParse(payload);
    if (!parsed.success) {
      throw new AnalysisError('INVALID_API_RESPONSE', 'The Space returned an analysis that does not match the F8 contract.', {
        issues: parsed.error.issues.slice(0, 12).map(issue => ({ path: issue.path.join('.'), message: issue.message })),
      });
    }
    return parsed.data;
  } catch (error) {
    if (error instanceof AnalysisError) throw error;
    if (error instanceof SyntaxError) throw new AnalysisError('INVALID_API_RESPONSE', 'The Space returned invalid JSON.');
    const message = error instanceof Error ? error.message : 'The Space analysis request failed.';
    if (message.includes('No endpoint matching')) throw new AnalysisError('API_ENDPOINT_MISMATCH', message);
    if (message.includes('Space metadata could not be loaded') || message.includes('Failed to fetch')) {
      throw new AnalysisError('API_OFFLINE', 'The Hugging Face Space could not be reached.');
    }
    throw new AnalysisError('ANALYSIS_FAILED', message);
  } finally {
    client?.close();
  }
}

export async function detectImage(_file: File, _signal?: AbortSignal): Promise<DetectResponse> {
  void _file; void _signal;
  throw new AnalysisError('ENDPOINT_UNAVAILABLE', 'This Gradio Space exposes analysis, not a raw detection endpoint.');
}
