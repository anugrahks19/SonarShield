import { Client } from '@gradio/client';
import type { HealthResponse } from '../types';
import { AnalysisError } from './errors';
import { gradioSpaceId } from '../config/env';

export const getHealth = async (signal?: AbortSignal): Promise<HealthResponse> => {
  if (signal?.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.');
  let client: Client | undefined;
  try {
    client = await Client.connect(gradioSpaceId);
    if (signal?.aborted) throw new AnalysisError('REQUEST_CANCELLED', 'The request was cancelled.');
    return {
      status: 'REACHABLE',
      schema_version: 'NOT_REPORTED',
      uptime_seconds: null,
      components: {},
      pipeline_version: 'NOT_REPORTED',
    };
  } catch (error) {
    if (error instanceof AnalysisError) throw error;
    throw new AnalysisError('API_OFFLINE', 'The Hugging Face Space could not be reached.');
  } finally {
    client?.close();
  }
};
