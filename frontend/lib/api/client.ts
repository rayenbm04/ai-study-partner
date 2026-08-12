/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * - Base URL comes from NEXT_PUBLIC_API_URL (see .env.local) — never
 *   hardcoded, mirroring the mobile app's EXPO_PUBLIC_API_URL convention.
 * - Access/refresh tokens live in ./storage (localStorage) — synchronous
 *   here (unlike the mobile client, which awaits SecureStore), but every
 *   method still returns a Promise so call sites can share the mobile
 *   client's shape.
 * - On a 401 (expired access token), this automatically tries one refresh
 *   + retry before giving up, so pages don't each need their own
 *   refresh-handling logic.
 * - Every backend domain error comes back as `{ detail: "message" }` (see
 *   backend/app/main.py's DomainError handler) — ApiError below normalizes
 *   that into a JS Error with a `.status` so callers can branch on it
 *   (e.g. 404 -> "not found", 409 -> "already exists") without re-parsing.
 */
import { storage } from "./storage";

const ACCESS_TOKEN_KEY = "auth_access_token";
const REFRESH_TOKEN_KEY = "auth_refresh_token";

function getApiBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set — copy .env.local.example to .env.local and point it at your backend."
    );
  }
  return url.replace(/\/+$/, "");
}

/** For call sites that need the absolute URL directly (e.g. a document
 * preview/download link) rather than going through this module's own
 * request helpers. */
export function apiUrl(path: string): string {
  return `${getApiBaseUrl()}${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export async function getAccessToken(): Promise<string | null> {
  return storage.getItem(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return storage.getItem(REFRESH_TOKEN_KEY);
}

export async function storeTokens(accessToken: string, refreshToken: string): Promise<void> {
  storage.setItem(ACCESS_TOKEN_KEY, accessToken);
  storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export async function clearTokens(): Promise<void> {
  storage.deleteItem(ACCESS_TOKEN_KEY);
  storage.deleteItem(REFRESH_TOKEN_KEY);
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean; // attach the access token — defaults to true
  /** Internal — prevents infinite refresh loops. Do not set from call sites. */
  _isRetry?: boolean;
};

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      // FastAPI's own request-validation errors (422) shape `detail` as a
      // list of {loc, msg, ...} instead of a plain string — surface the
      // first message rather than "[object Object]".
      return body.detail[0]?.msg ?? "Invalid request.";
    }
  } catch {
    // response body wasn't JSON — fall through to the generic message below.
  }
  return `Request failed (${response.status}).`;
}

let refreshInFlight: Promise<string | null> | null = null;

/** Calls POST /auth/refresh once, sharing the in-flight promise across
 * concurrent 401s so a page that fires several requests at once doesn't
 * trigger a refresh storm. Returns the new access token, or null if the
 * refresh token is gone/invalid (caller should treat that as logged out). */
async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return null;

    const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      await clearTokens();
      return null;
    }
    const tokens = await response.json();
    await storeTokens(tokens.access_token, tokens.refresh_token);
    return tokens.access_token as string;
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, _isRetry = false } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && auth && !_isRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiRequest<T>(path, { ...options, _isRetry: true });
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Sibling to apiRequest for multipart/form-data uploads (file uploads only
 * — always POST). Content-Type is deliberately left unset so fetch sets its
 * own multipart boundary; everything else (auth header, 401-refresh-retry,
 * error parsing) mirrors apiRequest exactly. */
export async function apiUpload<T>(path: string, formData: FormData, _isRetry = false): Promise<T> {
  const headers: Record<string, string> = {};
  const token = await getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (response.status === 401 && !_isRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiUpload<T>(path, formData, true);
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response));
  }
  return (await response.json()) as T;
}
