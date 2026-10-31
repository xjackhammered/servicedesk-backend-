/**
 * Tiny fetch wrapper:
 *  - attaches the JWT access token
 *  - refreshes it once on a 401 and retries
 *  - turns the backend error envelope into an ApiError
 */
const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
export const WS_URL = API_URL.replace(/^http/, 'ws');

const ACCESS_KEY = 'sd_access';
const REFRESH_KEY = 'sd_refresh';

export const tokenStore = {
  get access() { return localStorage.getItem(ACCESS_KEY); },
  get refresh() { return localStorage.getItem(REFRESH_KEY); },
  set({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  constructor(status, code, message, details = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let authLostHandler = null;
export function setAuthLostHandler(fn) { authLostHandler = fn; }

function jwtExpiry(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.exp * 1000;
  } catch {
    return null;
  }
}

let refreshPromise = null;

/** Exchange the refresh token for a new access token (one call at a time). */
export function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;
  const refresh = tokenStore.refresh;
  if (!refresh) return Promise.reject(new ApiError(401, 'unauthenticated', 'Not signed in.'));

  refreshPromise = fetch(`${API_URL}/api/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
    .then(async (res) => {
      if (!res.ok) {
        tokenStore.clear();
        throw new ApiError(401, 'unauthenticated', 'Your session expired. Please sign in again.');
      }
      const data = await res.json();
      tokenStore.set(data);
      return data.access;
    })
    .finally(() => { refreshPromise = null; });
  return refreshPromise;
}

/** Returns a token that is valid for at least ~30s, refreshing if needed. */
export async function getValidAccessToken() {
  const token = tokenStore.access;
  if (!token) return null;
  const expiresAt = jwtExpiry(token);
  if (expiresAt && expiresAt - Date.now() < 30_000) {
    try { return await refreshAccessToken(); } catch { return null; }
  }
  return token;
}

async function parseBody(res) {
  const text = await res.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch { return null; }
}

function toApiError(status, data) {
  if (data?.error) {
    const { code, message, details } = data.error;
    return new ApiError(status, code, details?.detail || message, details);
  }
  return new ApiError(status, 'error', data?.detail || `Request failed (${status}).`);
}

export async function api(path, { method = 'GET', body, params, auth = true } = {}) {
  const url = new URL(`${API_URL}/api${path}`);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });

  const send = (token) =>
    fetch(url, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

  let res;
  try {
    res = await send(auth ? await getValidAccessToken() : null);
    if (res.status === 401 && auth) {
      try {
        res = await send(await refreshAccessToken());
      } catch {
        authLostHandler?.();
        throw new ApiError(401, 'unauthenticated', 'Your session expired. Please sign in again.');
      }
    }
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Is the backend running?');
  }

  const data = await parseBody(res);
  if (!res.ok) throw toApiError(res.status, data);
  return data;
}
