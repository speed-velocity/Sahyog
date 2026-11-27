import { API_BASE_URL, REQUEST_TIMEOUT_MS } from './config';
import type { ApiErrorBody } from './types';

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;

  constructor(message: string, options: { status?: number | null; code: string }) {
    super(message);
    this.name = 'ApiError';
    this.status = options.status ?? null;
    this.code = options.code;
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function extractErrorCode(body: ApiErrorBody | null, status: number): string {
  const code = body?.error?.code;
  return typeof code === 'string' && code.length > 0 ? code : `HTTP_${status}`;
}

function extractErrorMessage(body: ApiErrorBody | null, status: number): string {
  const message = body?.error?.message;
  if (typeof message === 'string' && message.length > 0) {
    return message;
  }
  if (typeof body?.detail === 'string' && body.detail.length > 0) {
    return body.detail;
  }
  if (status === 404) {
    return 'The requested SAHYOG record was not found.';
  }
  if (status >= 500) {
    return 'The SAHYOG backend returned an error.';
  }
  return `The SAHYOG backend rejected the request (HTTP ${status}).`;
}

async function readJsonBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export async function getJson<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? REQUEST_TIMEOUT_MS;
  let timedOut = false;

  const timeoutHandle = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  const forwardExternalAbort = () => controller.abort();
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener('abort', forwardExternalAbort, { once: true });
    }
  }

  try {
    const token = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('sahyog_token') : null;
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'GET',
      headers,
      signal: controller.signal,
    });

    const body = (await readJsonBody(response)) as ApiErrorBody | null;

    if (!response.ok) {
      throw new ApiError(extractErrorMessage(body, response.status), {
        status: response.status,
        code: extractErrorCode(body, response.status),
      });
    }

    if (body === null) {
      throw new ApiError('The SAHYOG backend returned an empty or unreadable response.', {
        status: response.status,
        code: 'INVALID_RESPONSE',
      });
    }

    return body as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (timedOut) {
      throw new ApiError('The SAHYOG backend did not respond in time.', { code: 'TIMEOUT' });
    }
    if (controller.signal.aborted) {
      throw new DOMException('Request aborted', 'AbortError');
    }
    throw new ApiError('Unable to reach the SAHYOG backend. Check that it is running.', {
      code: 'NETWORK_ERROR',
    });
  } finally {
    clearTimeout(timeoutHandle);
    options.signal?.removeEventListener('abort', forwardExternalAbort);
  }
}
