export function safeMessage(value: unknown, secret?: string, depth?: number): string;
export function describeGradioError(error: unknown, options?: {secret?: string; now?: number; authenticated?: boolean}): {
  code: string; message: string; details: Record<string, unknown>; status: number;
};
