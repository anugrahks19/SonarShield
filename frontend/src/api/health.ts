import type { HealthResponse } from '../types';
import { requestJson } from './client';
import { healthSchema } from './schema';

export const getHealth = (signal?: AbortSignal): Promise<HealthResponse> => requestJson('/health', { schema: healthSchema, signal, timeoutMs: 8000 });
