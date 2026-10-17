import { getApiBaseUrl } from '@/data/api/config';
import type { ApiErrorBody } from '@/data/types/api';

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
};

export async function apiRequest<T>(
  path: string,
  { method = 'GET', body, token, signal }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const url = `${getApiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch {
    throw new ApiError(0, 'Network unavailable');
  }

  if (!response.ok) {
    let message = response.statusText;
    let code: string | undefined;
    try {
      const err = (await response.json()) as ApiErrorBody;
      message = err.error?.message ?? message;
      code = err.error?.code;
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, message, code);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
