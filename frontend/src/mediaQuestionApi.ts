import { getPrivateJson, postPrivateJson } from './api';
import { fetchWithAuth } from './authClient';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

export type QuestionMediaRole = 'primary' | 'poster' | 'fallback' | 'explanation';

export type QuestionMediaLink = {
  id: string;
  question_id: string;
  media_id: string;
  role: QuestionMediaRole;
  display_order: number;
  created_at: string;
};

export function listQuestionMedia(questionId: string): Promise<QuestionMediaLink[]> {
  return getPrivateJson<QuestionMediaLink[]>(
    `/api/v1/media-library/questions/${encodeURIComponent(questionId)}`,
  );
}

export function linkQuestionMedia(
  questionId: string,
  mediaId: string,
  role: QuestionMediaRole = 'primary',
  displayOrder = 0,
): Promise<QuestionMediaLink> {
  return postPrivateJson<QuestionMediaLink>(
    `/api/v1/media-library/questions/${encodeURIComponent(questionId)}/links`,
    { media_id: mediaId, role, display_order: displayOrder },
  );
}

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

export async function unlinkQuestionMedia(questionId: string, linkId: string): Promise<void> {
  const csrf = await getCsrfToken();
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/media-library/questions/${encodeURIComponent(questionId)}/links/${encodeURIComponent(linkId)}`,
    {
      method: 'DELETE',
      headers: csrf ? { 'X-CSRF-Token': csrf } : {},
    },
  );
  if (!response.ok) {
    let message = `Suppression impossible (${response.status})`;
    try {
      const payload = await response.json() as { detail?: string | { message?: string } };
      if (typeof payload.detail === 'string') message = payload.detail;
      else if (payload.detail?.message) message = payload.detail.message;
    } catch {
      // Keep the HTTP fallback.
    }
    throw new Error(message);
  }
}
