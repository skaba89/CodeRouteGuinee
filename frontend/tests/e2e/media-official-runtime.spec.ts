import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';

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

type OfficialMediaQuestion = {
  id: string;
  number: number;
  category: string;
  text: string;
  options: string[];
  media_url: string;
  media_type: 'video';
  media_alt: string;
  media_poster_url: string;
  media_fallback_url: string;
  media_source: 'normalized';
  media_degraded: boolean;
  audio_url: null;
};

const QUESTION: OfficialMediaQuestion = {
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

async function mockAuthenticatedCandidate(page: Page) {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: 4_102_444_800 }));
    window.localStorage.setItem('coderoute-auth-token', `e30.${payload}.sig`);
    window.localStorage.setItem('coderoute-refresh-token', 'media-official-refresh-token');
    window.sessionStorage.removeItem('coderoute:official-exam:active-attempt');
  });

  await page.route('**/api/v1/auth/me', route => route.fulfill({ json: CANDIDATE }));
  await page.route('**/api/v1/auth/csrf-token', route => route.fulfill({ json: { csrf_token: 'csrf-media-official' } }));
}

async function mockOfficialExam(page: Page, question: OfficialMediaQuestion, attemptId = ATTEMPT_ID) {
  await page.route('**/api/v1/exams/start-from-booking', route => route.fulfill({
    json: {
      id: attemptId,
      candidate_id: 'candidate-record-media-official',
      session_id: 'session-media-official',
      status: 'started',
      score: null,
      passed: null,
    },
  }));

  await page.route(`**/api/v1/exams/${attemptId}/questions*`, route => route.fulfill({
    json: {
      attempt_id: attemptId,
      questions: [question],
      duration_seconds: 1_800,
      threshold: 35,
    },
  }));

  await page.route(`**/api/v1/exams/${attemptId}/status`, route => route.fulfill({
    json: {
      attempt_id: attemptId,
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

  await page.route(`**/api/v1/exams/${attemptId}/answers`, route => route.fulfill({
    json: {
      attempt_id: attemptId,
      answers: {},
      saved: 0,
      status: 'started',
    },
  }));
}

async function startOfficialExam(page: Page) {
  await page.goto('/#/exam');
  await expect(page.getByText('Code de la Route — Catégorie B')).toBeVisible();
  await page.getByPlaceholder('GN-CONV-2026-000001').fill('GN-CONV-MEDIA-OFFICIAL-001');
  await page.getByRole('button', { name: "Démarrer l'examen officiel" }).click();
  await expect(page.getByRole('main', { name: 'Examen officiel en cours' })).toBeVisible();
}

test('examen officiel utilise le poster et le fallback validés par le backend', async ({ page }) => {
  await mockAuthenticatedCandidate(page);
  await mockOfficialExam(page, QUESTION);
  await startOfficialExam(page);

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

test('examen officiel normalise une vidéo Cloudinary MOV/WebM pour le navigateur', async ({ page }) => {
  const cloudinaryOriginal = 'https://res.cloudinary.com/coderoute-guinee/video/upload/v1723456789/exams/roundabout.mov';
  const cloudinaryPlayable = 'https://res.cloudinary.com/coderoute-guinee/video/upload/f_auto,q_auto/v1723456789/exams/roundabout.mov';
  const cloudinaryQuestion: OfficialMediaQuestion = {
    ...QUESTION,
    id: 'q-official-cloudinary-video-1',
    media_url: cloudinaryOriginal,
  };

  // The browser must exercise the transformed Cloudinary URL without making
  // this E2E depend on an external/fictitious Cloudinary asset. Serve the
  // versioned six-second MP4 fixture under that transformed URL so a real
  // HTMLVideoElement can load and remain mounted deterministically.
  const localVideoPath = path.resolve(process.cwd(), 'public/media/exam/guinea/roundabout-approach-demo.mp4');
  await page.route(cloudinaryPlayable, route => route.fulfill({
    path: localVideoPath,
    contentType: 'video/mp4',
  }));

  await mockAuthenticatedCandidate(page);
  await mockOfficialExam(page, cloudinaryQuestion, 'attempt-media-cloudinary-001');
  await startOfficialExam(page);

  const video = page.getByTestId('exam-media-video');
  await expect(video).toBeVisible();
  await expect(video).toHaveAttribute('src', cloudinaryPlayable);
  await expect(video).toHaveAttribute('poster', POSTER_URL);
});
