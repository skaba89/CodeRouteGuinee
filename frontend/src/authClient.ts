const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const AUTH_TOKEN_STORAGE_KEY = 'coderoute-auth-token';

export type AuthToken = {
  access_token: string;
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

export function getAccessToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function getAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function loginUser(email: string, password: string): Promise<AuthToken> {
  const body = new URLSearchParams();
  body.set('username', email);
  body.set('password', password);

  const token = await readJson<AuthToken>(await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  }));

  setAccessToken(token.access_token);
  return token;
}

export async function registerUser(payload: RegisterPayload): Promise<AuthUser> {
  return readJson<AuthUser>(await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }));
}

export async function getCurrentUser(): Promise<AuthUser> {
  return readJson<AuthUser>(await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: getAuthHeaders(),
  }));
}

export function logoutUser(): void {
  clearAccessToken();
}
