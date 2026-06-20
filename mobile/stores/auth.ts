/**
 * Store Zustand — Authentification CodeRoute Guinée Mobile
 * Partage la logique JWT avec le frontend web via les mêmes endpoints API.
 */
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  currentUser: { id: string; email: string; full_name: string; role: string } | null;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  restoreSession: () => Promise<void>;
}

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  currentUser: null,
  isLoading: true,

  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const resp = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (!resp.ok) throw new Error('Identifiants incorrects');
    const data = await resp.json();
    
    await SecureStore.setItemAsync('access_token', data.access_token);
    await SecureStore.setItemAsync('refresh_token', data.refresh_token);
    
    // Récupérer le profil
    const me = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    }).then(r => r.json());

    set({ accessToken: data.access_token, refreshToken: data.refresh_token, currentUser: me });
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('access_token');
    await SecureStore.deleteItemAsync('refresh_token');
    set({ accessToken: null, refreshToken: null, currentUser: null });
  },

  refreshSession: async () => {
    const rt = get().refreshToken ?? await SecureStore.getItemAsync('refresh_token');
    if (!rt) throw new Error('Pas de refresh token');
    
    const resp = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!resp.ok) throw new Error('Session expirée');
    const data = await resp.json();
    
    await SecureStore.setItemAsync('access_token', data.access_token);
    await SecureStore.setItemAsync('refresh_token', data.refresh_token);
    set({ accessToken: data.access_token, refreshToken: data.refresh_token });
  },

  restoreSession: async () => {
    try {
      const at = await SecureStore.getItemAsync('access_token');
      const rt = await SecureStore.getItemAsync('refresh_token');
      if (!at) { set({ isLoading: false }); return; }
      
      const me = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${at}` },
      });
      
      if (me.ok) {
        set({ accessToken: at, refreshToken: rt, currentUser: await me.json() });
      } else if (rt) {
        await get().refreshSession();
      }
    } catch {
      await SecureStore.deleteItemAsync('access_token');
    } finally {
      set({ isLoading: false });
    }
  },
}));
