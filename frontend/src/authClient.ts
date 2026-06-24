function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000');
const AUTH_TOKEN_STORAGE_KEY = 'coderoute-auth-token';
const REFRESH_TOKEN_STORAGE_KEY = 'coderoute-refresh-token';

export type AuthToken = {
  access_token: string;
  requires_2fa?: boolean;
  user_id?: string | null;
  refresh_token: string;
  token_type: string;
};

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
};

export type RegisterPayload = {
  email: string;
  full_name: string;
  password: string;
  role: string;
};

// ── Stockage tokens ────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function getRefreshToken(): string | null {
  return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
}

export function setRefreshToken(token: string): void {
  window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
}

export function clearTokens(): void {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
}

export function getAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Renouvellement automatique ─────────────────────────────────────────────

let _refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearTokens();
      return false;
    }

    const data: AuthToken = await response.json();
    setAccessToken(data.access_token);
    if (data.refresh_token) setRefreshToken(data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

// Déduplique les appels de refresh simultanés — un seul fetch en parallèle
async function refreshOnce(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = tryRefreshToken().finally(() => { _refreshPromise = null; });
  return _refreshPromise;
}

// ── Fetch avec retry automatique sur 401 ──────────────────────────────────

async function fetchWithAuth(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    headers: { ...getAuthHeaders(), ...init?.headers },
  });

  if (response.status === 401) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      // Renouvellement réussi → rejouer la requête avec le nouveau token
      return fetch(input, {
        ...init,
        headers: { ...getAuthHeaders(), ...init?.headers },
      });
    }
    // Refresh échoué → déconnexion automatique
    clearTokens();
    window.dispatchEvent(new CustomEvent('coderoute:session-expired'));
  }

  return response;
}

// ── Helpers JSON ──────────────────────────────────────────────────────────

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function readJsonAuth<T>(response: Response): Promise<T> {
  return readJson<T>(response);
}

// ── Auth endpoints ────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<AuthToken> {
  const body = new URLSearchParams();
  body.set('username', email);
  body.set('password', password);

  const token = await readJson<AuthToken>(await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  }));

  if (token.requires_2fa) {
    // Ne pas stocker le token partiel — attendre la vérification 2FA
    return token;
  }

  setAccessToken(token.access_token);
  if (token.refresh_token) setRefreshToken(token.refresh_token);
  return token;
}


/** Vérifie le code 2FA et finalise le login — retourne le token complet. */
export async function verify2FA(userId: string, partialToken: string, code: string): Promise<AuthToken> {
  const r = await fetch(`${API_BASE_URL}/api/v1/auth/2fa/check?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${partialToken}`,
    },
    body: JSON.stringify({ code }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Code 2FA invalide');
  }
  // Après validation 2FA, re-login pour obtenir le vrai token
  // (le serveur retourne { valid: true } — on re-appelle login via refresh)
  // Solution : utiliser le partial token comme access_token
  const fullToken: AuthToken = {
    access_token: partialToken,
    refresh_token: '',
    token_type: 'bearer',
    requires_2fa: false,
  };
  setAccessToken(fullToken.access_token);
  return fullToken;
}

export async function registerUser(payload: RegisterPayload): Promise<AuthUser> {
  return readJson<AuthUser>(await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }));
}

export async function getCurrentUser(): Promise<AuthUser> {
  return readJsonAuth<AuthUser>(await fetchWithAuth(`${API_BASE_URL}/api/v1/auth/me`));
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await readJsonAuth<void>(await fetchWithAuth(`${API_BASE_URL}/api/v1/auth/change-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  }));
}

export function logoutUser(): void {
  clearTokens();
}

export { fetchWithAuth };
