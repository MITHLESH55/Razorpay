/**
 * RiskOrbit — Unified API Client & Request Handler
 *
 * Configures the base URL from import.meta.env.VITE_API_BASE_URL (default: http://127.0.0.1:8001),
 * injects Bearer authentication tokens, handles structured API errors, and manages X-Request-ID tracing.
 */

export const API_BASE_URL =
  (typeof import.meta !== 'undefined' && (import.meta as any).env && (import.meta as any).env.VITE_API_BASE_URL) ||
  'http://127.0.0.1:8001';

export class ApiError extends Error {
  public status: number;
  public code?: string;
  public details?: any;
  public requestId?: string;
  public caseId?: string;

  constructor(message: string, status: number, data?: any, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.requestId = requestId;
    if (data && typeof data === 'object') {
      this.code = data.code || data.detail?.code;
      this.details = data.details || data.detail;
      this.requestId = data.request_id || requestId;
      this.caseId = data.case_id;
    }
  }
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, any>;
  skipAuth?: boolean;
}

/**
 * Generates a unique client-side request tracing identifier.
 */
export function generateRequestId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `req_${crypto.randomUUID()}`;
  }
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Global token storage helpers
 */
const TOKEN_KEY = 'riskorbit_auth_token';

export function getAuthToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string, persist = true): void {
  try {
    if (persist) {
      localStorage.setItem(TOKEN_KEY, token);
    }
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {}
}

export function clearAuthToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {}
}

/**
 * Core fetch wrapper with JSON serialization, Bearer auth, X-Request-ID, and typed responses
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, skipAuth = false, headers = {}, ...restOptions } = options;

  let url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  const clientRequestId = generateRequestId();

  const reqHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'X-Request-ID': clientRequestId,
    ...(headers as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      reqHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...restOptions,
      headers: reqHeaders,
    });
  } catch (err: any) {
    throw new ApiError(
      `Network connection failure: Unable to reach RiskOrbit API at ${API_BASE_URL}. Ensure backend is running.`,
      0,
      { details: err.message },
      clientRequestId
    );
  }

  const serverRequestId = response.headers.get('x-request-id') || clientRequestId;

  let data: any;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await response.text();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errorMsg =
      (data && typeof data === 'object' && (data.message || data.detail || data.error)) ||
      `HTTP Error ${response.status}: ${response.statusText}`;

    // On 401 Unauthorized, dispatch global session expiry event if needed
    if (response.status === 401 && !skipAuth) {
      window.dispatchEvent(new CustomEvent('riskorbit:unauthorized'));
    }

    throw new ApiError(errorMsg, response.status, data, serverRequestId);
  }

  return data as T;
}
