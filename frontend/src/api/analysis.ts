import { Client } from '@gradio/client';
import type { AnalyzeResponse, DetectResponse } from '../types';
import { analyzeSchema } from './schema';
import { AnalysisError, responseError } from './errors';
import { gradioSpaceId } from '../config/env';
import { classifyGradioError } from './gradioError';

export async function analyzeImage(file: File, signal?: AbortSignal): Promise<AnalyzeResponse> {
  const cancelled = () => { if (signal?.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.'); };
  cancelled();
  let client: Client | undefined;
  try {
    // Upload bytes directly to the public Space; only the small reference goes to Vercel.
    client = await Client.connect(gradioSpaceId, { record_history: false });
    cancelled();
    const root = client.config?.root;
    if (!root) throw new AnalysisError('API_OFFLINE', 'The Space upload configuration could not be loaded.');
    const upload = await client.upload_files(root, [file]);
    cancelled();
    if (upload.error) throw new Error(upload.error);
    if (upload.files?.length !== 1) throw new AnalysisError('INVALID_API_RESPONSE', 'The Space did not return an uploaded image reference.');
    const response = await fetch('/api/analyze', {
      method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file: { path: upload.files[0], orig_name: file.name, mime_type: file.type || (/\.png$/i.test(file.name) ? 'image/png' : 'image/jpeg'), size: file.size } }),
    });
    cancelled();
    const payload: unknown = await response.json();
    if (!response.ok) throw responseError(response.status, payload);
    const parsed = analyzeSchema.safeParse(payload);
    if (!parsed.success) {
      throw new AnalysisError('INVALID_API_RESPONSE', 'The Space returned an analysis that does not match the F8 contract.', {
        issues: parsed.error.issues.slice(0, 12).map(issue => ({ path: issue.path.join('.'), message: issue.message })),
      });
    }
    cancelled();
    return parsed.data;
  } catch (error) {
    cancelled();
    throw classifyGradioError(error);
  } finally {
    client?.close();
  }
}

export async function detectImage(_file: File, _signal?: AbortSignal): Promise<DetectResponse> {
  void _file; void _signal;
  throw new AnalysisError('ENDPOINT_UNAVAILABLE', 'This Gradio Space exposes analysis, not a raw detection endpoint.');
}
