import { getCurrentIdToken } from '../auth/firebase';

export interface APIErrorPayload {
  code: string;
  message: string;
  retryable?: boolean;
  details?: any[];
}

export class SurgeAPIError extends Error {
  code: string;
  status: number;
  retryable: boolean;
  details?: any[];

  constructor(status: number, payload: APIErrorPayload) {
    super(payload.message || `API Error: ${payload.code}`);
    this.name = 'SurgeAPIError';
    this.status = status;
    this.code = payload.code || 'UNKNOWN_ERROR';
    this.retryable = !!payload.retryable;
    this.details = payload.details;
  }
}

const BASE_URL = ''; // Relative path leverages Vite dev proxy in dev and same-origin in prod

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(options.headers || {});
  
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Non-negotiable rule 1: Always attach Firebase ID token when available
  if (!headers.has('Authorization')) {
    try {
      const token = await getCurrentIdToken();
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
    } catch {
      // Ignore token fetch errors and proceed as unauthenticated/demo
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let payload: APIErrorPayload = {
      code: `HTTP_${response.status}`,
      message: response.statusText,
    };
    try {
      const data = await response.json();
      if (data && data.error) {
        payload = data.error;
      } else if (data && data.detail) {
        payload.message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Ignore JSON parse failure on non-JSON response
    }
    throw new SurgeAPIError(response.status, payload);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
