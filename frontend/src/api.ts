import { GenerationRequest, GenerationStatusResponse } from './types';

const API_BASE = '/api';

export class ApiError extends Error {
  statusCode: number;
  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
  }
}

export async function startGeneration(
  request: GenerationRequest,
  idempotencyKey?: string
): Promise<GenerationStatusResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  const response = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });

  if (response.status === 429) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(data.detail || 'Server is currently at capacity. Please try again shortly.', 429);
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = data.detail || `Server returned error (${response.status})`;
    throw new ApiError(message, response.status);
  }

  return response.json();
}

export async function getTaskStatus(taskId: string): Promise<GenerationStatusResponse> {
  const response = await fetch(`${API_BASE}/status/${taskId}`);

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(data.detail || `Failed to fetch status (${response.status})`, response.status);
  }

  return response.json();
}

export function getDownloadUrl(taskId: string): string {
  return `${API_BASE}/download/${taskId}`;
}
