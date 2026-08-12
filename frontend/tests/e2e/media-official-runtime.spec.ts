import { expect, test, type Page } from '@playwright/test';

const ATTEMPT_ID = 'attempt-media-official-001';
const VIDEO_URL = '/media/exam/guinea/roundabout-approach-demo.mp4?v=official-runtime';
const POSTER_URL = '/media/exam/guinea/stop-conakry.webp?v=official-poster';
const FALLBACK_URL = '/media/exam/guinea/no-entry-conakry.webp?v=official-fallback';

// Tiny valid H.264/MP4 fixture generated only for the browser-delivery contract.
// Keeping the payload inline makes this test independent from external
// Cloudinary availability and from the demo media pack's playback semantics.
const INLINE_MP4_BASE64 = 'AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAOMbW9vdgAAAGxtdmhkAAAAAAAAAAAAAAAAAAAD6AAAARgAAQAAAQAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAArd0cmFrAAAAXHRraGQAAAADAAAAAAAAAAAAAAABAAAAAAAAARgAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAABAAAAAQAAAAAAAkZWR0cwAAABxlbHN0AAAAAAAAAAEAAAEYAAAEAAABAAAAAAIvbWRpYQAAACBtZGhkAAAAAAAAAAAAAAAAAAAyAAAADgBVxAAAAAAALWhkbHIAAAAAAAAAAHZpZGUAAAAAAAAAAAAAAABWaWRlb0hhbmRsZXIAAAAB2m1pbmYAAAAUdm1oZAAAAAEAAAAAAAAAAAAAACRkaW5mAAAAHGRyZWYAAAAAAAAAAQAAAAx1cmwgAAAAAQAAAZpzdGJsAAAAvnN0c2QAAAAAAAAAAQAAAK5hdmMxAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAABAAEABIAAAASAAAAAAAAAABFUxhdmM2MS4xOS4xMDEgbGlieDI2NAAAAAAAAAAAAAAAGP//AAAANGF2Y0MBZAAK/+EAF2dkAAqs2V7ARAAAAwAEAAADAMg8SJZYAQAGaOvjyyLA/fj4AAAAABBwYXNwAAAAAQAAAAEAAAAUYnRydAAAAAAAAFfVAAAAAAAAABhzdHRzAAAAAAAAAAEAAAAHAAACAAAAABRzdHNzAAAAAAAAAAEAAAABAAAASGN0dHMAAAAAAAAABwAAAAEAAAQAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAGAAAAAAEAAAIAAAAAHHN0c2MAAAAAAAAAAQAAAAEAAAAHAAAAAQAAADBzdHN6AAAAAAAAAAAAAAAHAAACxQAAAAwAAAAMAAAADAAAAAwAAAASAAAADAAAABRzdGNvAAAAAAAAAAEAAAO8AAAAYXVkdGEAAABZbWV0YQAAAAAAAAAhaGRscgAAAAAAAAAAbWRpcmFwcGwAAAAAAAAAAAAAAAAsaWxzdAAAACSpdG9vAAAAHGRhdGEAAAABAAAAAExhdmY2MS43LjEwMwAAAAhmcmVlAAADG21kYXQAAAKuBgX//6rcRem95tlIt5Ys2CDZI+7veDI2NCAtIGNvcmUgMTY0IHIzMTA4IDMxZTE5ZjkgLSBILjI2NC9NUEVHLTQgQVZDIGNvZGVjIC0gQ29weWxlZnQgMjAwMy0yMDIzIC0gaHR0cDovL3d3dy52aWRlb2xhbi5vcmcveDI2NC5odG1sIC0gb3B0aW9uczogY2FiYWM9MSByZWY9MyBkZWJsb2NrPTE6MDowIGFuYWx5c2U9MHgzOjB4MTEzIG1lPWhleCBzdWJtZT03IHBzeT0xIHBzeV9yZD0xLjAwOjAuMDAgbWl4ZWRfcmVmPTEgbWVfcmFuZ2U9MTYgY2hyb21hX21lPTEgdHJlbGxpcz0xIDh4OGRjdD0xIGNxbT0wIGRlYWR6b25lPTIxLDExIGZhc3RfcHNraXA9MSBjaHJvbWFfcXBfb2Zmc2V0PS0yIHRocmVhZHM9MSBsb29rYWhlYWRfdGhyZWFkcz0xIHNsaWNlZF90aHJlYWRzPTAgbnI9MCBkZWNpbWF0ZT0xIGludGVybGFjZWQ9MCBibHVyYXlfY29tcGF0PTAgY29uc3RyYWluZWRfaW50cmE9MCBiZnJhbWVzPTMgYl9weXJhbWlkPTIgYl9hZGFwdD0xIGJfYmlhcz0wIGRpcmVjdD0xIHdlaWdodGI9MSBvcGVuX2dvcD0wIHdlaWdodHA9MiBrZXlpbnQ9MjUwIGtleWludF9taW49MjUgc2NlbmVjdXQ9NDAgaW50cmFfcmVmcmVzaD0wIHJjX2xvb2thaGVhZD00MCByYz1jcmYgbWJ0cmVlPTEgY3JmPTIzLjAgcWNvbXA9MC42MCBxcG1pbj0wIHFwbWF4PTY5IHFwc3RlcD00IGlwX3JhdGlvPTEuNDAgYXE9MToxLjAwAIAAAAAPZYiEADf//vbw/gU2VgTBAAAACEGaJGxDP/7gAAAACEGeQniF/8GBAAAACAGeYXRCv8SAAAAACAGeY2pCv8SBAAAADkGaZkmoQWiZTBTwr/7BAAAACAGehWpCv8SB';

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

  let transformedRequestSeen = false;
  await page.route('https://res.cloudinary.com/**', route => {
    if (route.request().url() !== cloudinaryPlayable) {
      return route.abort();
    }
    transformedRequestSeen = true;
    return route.fulfill({
      body: Buffer.from(INLINE_MP4_BASE64, 'base64'),
      contentType: 'video/mp4',
      headers: {
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'no-store',
      },
    });
  });

  await mockAuthenticatedCandidate(page);
  await mockOfficialExam(page, cloudinaryQuestion, 'attempt-media-cloudinary-001');
  await startOfficialExam(page);

  const video = page.getByTestId('exam-media-video');
  await expect(video).toBeVisible();
  await expect(video).toHaveAttribute('src', cloudinaryPlayable);
  await expect(video).toHaveAttribute('poster', POSTER_URL);
  await expect.poll(() => transformedRequestSeen).toBe(true);
});
