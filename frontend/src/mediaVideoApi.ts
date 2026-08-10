import { fetchWithAuth } from './authClient';
import type { MediaAsset } from './mediaApi';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

async function getCsrfToken(): Promise<string> {
  const fromCookie = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1];
  if (fromCookie) return fromCookie;

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/csrf-token`, {
    credentials: 'include',
  });
  if (!response.ok) return '';
  const payload = await response.json() as { csrf_token?: string };
  return payload.csrf_token ?? '';
}

export async function configureVideoSupportMedia(
  videoId: string,
  posterMediaId: string,
  fallbackMediaId: string,
): Promise<MediaAsset> {
  const csrf = await getCsrfToken();
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/media-library/assets/${encodeURIComponent(videoId)}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      },
      body: JSON.stringify({
        poster_media_id: posterMediaId,
        fallback_media_id: fallbackMediaId,
      }),
    },
  );

  if (!response.ok) {
    let message = `Configuration vidéo impossible (${response.status})`;
    try {
      const payload = await response.json() as { detail?: string | { message?: string } };
      if (typeof payload.detail === 'string') message = payload.detail;
      else if (payload.detail?.message) message = payload.detail.message;
    } catch {
      // Keep the HTTP fallback.
    }
    throw new Error(message);
  }
  return response.json() as Promise<MediaAsset>;
}
