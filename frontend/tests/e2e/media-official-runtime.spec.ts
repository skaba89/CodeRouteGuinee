import { expect, test } from '@playwright/test';

const ATTEMPT_ID = 'attempt-media-official-001';
const VIDEO_URL = '/media/exam/guinea/roundabout-approach-demo.mp4?v=official-runtime';
const POSTER_URL = '/media/exam/guinea/stop-conakry.webp?v=official-poster';
const FALLBACK_URL = '/media/exam/guinea/no-entry-conakry.webp?v=official-fallback';

const CANDIDATE = {
  id: 'candidate-media-official',
  email: 'candidate.media.official@coderoute.test',
  full_name: 'Mamadou Media Officiel',
  role: 'candidate',
  is_active: true,
  center_id: null,
};

const QUESTION = {
  id: 'q-official-video-1',
  number: 1,
  category: 'Priorités',
  text: 'À l’approche de ce giratoire, quelle conduite adopter ?',
  options: ['Accélérer', 'Céder le passage', 'S’arrêter au milieu', 'Klaxonner'],
  media_url: VIDEO_URL,
  media_type: 'video',
  media_alt: 'Approche d’un giratoire en Guinée',
  media_poster_url: POSTER_URL,
  media_fallback_url: FALLBACK_URL,
  media_source: 'normalized',
  media_degraded: false,
  audio_url: null,
};

async function mockAuthenticatedCandidate(page: Parameters<typeof test>[0] extends never ? never : any) {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: 4_102_444_800 }));
    window.localStorage.setItem('coderoute-auth-token', `e30.${payload}.sig`);
    window.localStorage.setItem('coderoute-refresh-token', 'media-official-refresh-token');
    window.sessionStorage.removeItem('coderoute:official-exam:active-attempt');
  });

  await page.route('**/api/v1/auth/me', (route: any) => route.fulfill({ json: CANDIDATE }));
  await page.route('**/api/v1/auth/csrf-token', (route: any) => route.fulfill({ json: { csrf_token: 'csrf-media-official' } }));
}

test('examen officiel utilise le poster et le fallback validés par le backend', async ({ page }) => {
  await mockAuthenticatedCandidate(page);

  await page.route('**/api/v1/exams/start-from-booking', route => route.fulfill({
    json: {
      id: ATTEMPT_ID,
      candidate_id: 'candidate-record-media-official',
      session_id: 'session-media-official',
      status: 'started',
      score: null,
      passed: null,
    },
  }));

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/questions*`, route => route.fulfill({
    json: {
      attempt_id: ATTEMPT_ID,
      questions: [QUESTION],
      duration_seconds: 1_800,
      threshold: 35,
    },
  }));

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/status`, route => route.fulfill({
    json: {
      attempt_id: ATTEMPT_ID,
      status: 'started',
      remaining_seconds: 1_799,
      elapsed_seconds: 1,
      total_seconds: 1_800,
      question_count: 1,
      score: null,
      passed: null,
      expired: false,
    },
  }));

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/answers`, route => route.fulfill({
    json: {
      attempt_id: ATTEMPT_ID,
      answers: {},
      saved: 0,
      status: 'started',
    },
  }));

  await page.goto('/#/exam');
  await expect(page.getByText('Code de la Route — Catégorie B')).toBeVisible();
  await page.getByPlaceholder('GN-CONV-2026-000001').fill('GN-CONV-MEDIA-OFFICIAL-001');
  await page.getByRole('button', { name: "Démarrer l'examen officiel" }).click();

  await expect(page.getByRole('main', { name: 'Examen officiel en cours' })).toBeVisible();

  const video = page.getByTestId('exam-media-video');
  await expect(video).toBeVisible();
  await expect(video).toHaveAttribute('src', VIDEO_URL);
  await expect(video).toHaveAttribute('poster', POSTER_URL);

  await video.dispatchEvent('error');

  const fallback = page.getByTestId('exam-media-video-fallback');
  await expect(fallback).toBeVisible();
  await expect(fallback).toHaveAttribute('src', FALLBACK_URL);
  await expect(page.getByText(/vidéo indisponible — image de secours affichée/i)).toBeVisible();
});
