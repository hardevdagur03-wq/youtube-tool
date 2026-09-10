export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string;
  errors: Array<{ code: string; field?: string; detail: string }> | null;
  request_id: string;
  timestamp: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public errors?: Array<{ code: string; field?: string; detail: string }>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Extract the actual data payload from a standardized API response.
 * Supports both wrapped `{success, data}` format and flat responses.
 */
export function unwrapResponse<T>(response: any): T {
  // Wrapped format: { success: true, data: {...} }
  if (response && typeof response === 'object' && 'success' in response && 'data' in response) {
    return response.data as T;
  }
  // Flat format: returned directly
  return response as T;
}

export function unwrap<T>(response: ApiResponse<T>): T {
  if (!response.success) {
    const msg = response.errors?.[0]?.detail || response.message || 'Request failed';
    throw new ApiError(msg, undefined, response.errors ?? undefined);
  }
  if (response.data === null || response.data === undefined) {
    throw new ApiError('Empty response');
  }
  return response.data;
}

export async function apiGet<T>(
  url: string,
  options?: { timeout?: number; signal?: AbortSignal },
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    options?.timeout ?? 30000,
  );

  try {
    const res = await fetch(url, {
      signal: options?.signal ?? controller.signal,
      headers: { 'Accept': 'application/json' },
    });

    clearTimeout(timeout);

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      let msg: string;
      let errs: Array<{ code: string; field?: string; detail: string }> | undefined;
      try {
        const json = JSON.parse(text);
        msg = json.errors?.[0]?.detail || json.message || `Server returned ${res.status}`;
        errs = json.errors;
      } catch {
        msg = text || `Server returned ${res.status}`;
      }
      throw new ApiError(msg, res.status, errs);
    }

    const json = await res.json() as ApiResponse<T>;
    return unwrap(json);
  } catch (err: unknown) {
    clearTimeout(timeout);
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('Request timed out');
    }
    if (err instanceof TypeError) {
      throw new ApiError('Network error: Unable to connect to server');
    }
    throw err;
  }
}

export async function apiPost<T>(
  url: string,
  body?: unknown,
  options?: { timeout?: number; signal?: AbortSignal },
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    options?.timeout ?? 30000,
  );

  try {
    const res = await fetch(url, {
      method: 'POST',
      signal: options?.signal ?? controller.signal,
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    clearTimeout(timeout);

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      let msg: string;
      let errs: Array<{ code: string; field?: string; detail: string }> | undefined;
      try {
        const json = JSON.parse(text);
        msg = json.errors?.[0]?.detail || json.message || `Server returned ${res.status}`;
        errs = json.errors;
      } catch {
        msg = text || `Server returned ${res.status}`;
      }
      throw new ApiError(msg, res.status, errs);
    }

    const json = await res.json() as ApiResponse<T>;
    return unwrap(json);
  } catch (err: unknown) {
    clearTimeout(timeout);
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('Request timed out');
    }
    if (err instanceof TypeError) {
      throw new ApiError('Network error: Unable to connect to server');
    }
    throw err;
  }
}

export async function apiDelete<T>(
  url: string,
  options?: { timeout?: number },
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    options?.timeout ?? 30000,
  );

  try {
    const res = await fetch(url, {
      method: 'DELETE',
      signal: controller.signal,
      headers: { 'Accept': 'application/json' },
    });

    clearTimeout(timeout);

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      let msg: string;
      try {
        const json = JSON.parse(text);
        msg = json.errors?.[0]?.detail || json.message || `Server returned ${res.status}`;
      } catch {
        msg = text || `Server returned ${res.status}`;
      }
      throw new ApiError(msg, res.status);
    }

    const json = await res.json() as ApiResponse<T>;
    return unwrap(json);
  } catch (err: unknown) {
    clearTimeout(timeout);
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('Request timed out');
    }
    if (err instanceof TypeError) {
      throw new ApiError('Network error: Unable to connect to server');
    }
    throw err;
  }
}
