import { expect, test, type Page, type Route } from '@playwright/test';

const ATTEMPT_ID = 'attempt-e2e-runtime-001';
const CANDIDATE = {
  id: 'user-e2e-candidate',
  email: 'candidate.e2e@coderoute.test',
  full_name: 'Mamadou Test',
  role: 'candidate',
  is_active: true,
  center_id: null,
};

const QUESTIONS = [
  {
    id: 'q-priority-1',
    number: 1,
    category: 'Priorités',
    text: 'À cette intersection, qui doit céder le passage ?',
    options: ['Le véhicule rouge', 'Le véhicule blanc', 'Les deux véhicules', 'Aucun véhicule'],
    media_url: null,
    media_type: null,
    media_alt: null,
    audio_url: null,
  },
  {
    id: 'q-signal-2',
    number: 2,
    category: 'Signalisation',
    text: 'Que signifie ce panneau ?',
    options: ['STOP', 'Cédez le passage', 'Sens interdit', 'Stationnement interdit'],
    media_url: null,
    media_type: null,
    media_alt: null,
    audio_url: null,
  },
];

function liveStatus(remainingSeconds = 1_199) {
  return {
    attempt_id: ATTEMPT_ID,
    status: 'started',
    remaining_seconds: remainingSeconds,
    elapsed_seconds: 1_800 - remainingSeconds,
    total_seconds: 1_800,
    question_count: QUESTIONS.length,
    score: null,
    passed: null,
    expired: remainingSeconds === 0,
  };
}

async function mockAuthenticatedCandidate(page: Page) {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: 4_102_444_800 }));
    window.localStorage.setItem('coderoute-auth-token', `e30.${payload}.sig`);
    window.localStorage.setItem('coderoute-refresh-token', 'e2e-refresh-token');
  });

  await page.route('**/api/v1/auth/me', route => route.fulfill({ json: CANDIDATE }));
  await page.route('**/api/v1/auth/csrf-token', route => route.fulfill({ json: { csrf_token: 'csrf-e2e' } }));
}

async function mockOfficialExam(
  page: Page,
  options: {
    remainingSeconds?: number;
    onAutosave?: (route: Route) => Promise<void> | void;
    onTimeoutSubmit?: (route: Route) => Promise<void> | void;
  } = {},
) {
  const remainingSeconds = options.remainingSeconds ?? 1_199;

  await page.route('**/api/v1/exams/start-from-booking', async route => {
    await route.fulfill({
      json: {
        id: ATTEMPT_ID,
        candidate_id: 'candidate-record-e2e',
        session_id: 'session-e2e',
        status: 'started',
        score: null,
        passed: null,
      },
    });
  });

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/questions*`, route => route.fulfill({
    json: {
      attempt_id: ATTEMPT_ID,
      questions: QUESTIONS,
      duration_seconds: 1_800,
      threshold: 35,
    },
  }));

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/status`, route => route.fulfill({
    json: liveStatus(remainingSeconds),
  }));

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/answers`, async route => {
    if (options.onAutosave) {
      await options.onAutosave(route);
      return;
    }
    await route.fulfill({
      json: { attempt_id: ATTEMPT_ID, saved: Object.keys(route.request().postDataJSON()?.answers ?? {}).length, status: 'started' },
    });
  });

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/timeout-submit`, async route => {
    if (options.onTimeoutSubmit) {
      await options.onTimeoutSubmit(route);
      return;
    }
    await route.fulfill({
      json: {
        id: ATTEMPT_ID,
        candidate_id: 'candidate-record-e2e',
        session_id: 'session-e2e',
        status: 'submitted',
        score: 1,
        passed: true,
      },
    });
  });

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/submit`, route => route.fulfill({
    json: {
      id: ATTEMPT_ID,
      candidate_id: 'candidate-record-e2e',
      session_id: 'session-e2e',
      status: 'submitted',
      score: 1,
      passed: true,
    },
  }));

  await page.route(`**/api/v1/exams/${ATTEMPT_ID}/results`, route => route.fulfill({
    json: {
      attempt_id: ATTEMPT_ID,
      candidate_name: 'Mamadou Test',
      score: 1,
      total: QUESTIONS.length,
      score_percent: 50,
      passed: true,
      threshold: 1,
      submitted_at: '2026-08-08T17:30:00',
      questions: QUESTIONS.map((question, index) => ({
        number: index + 1,
        question_id: question.id,
        category: question.category,
        text: question.text,
        options: question.options,
        given_answer: index === 0 ? question.options[1] : null,
        correct_answer: index === 0 ? question.options[1] : question.options[0],
        is_correct: index === 0,
        explanation: 'Explication de test disponible uniquement après soumission.',
      })),
    },
  }));
}

async function openOfficialExam(page: Page) {
  await page.goto('/#/exam');
  await expect(page.getByText('Code de la Route — Catégorie B')).toBeVisible();
  await page.getByPlaceholder('GN-CONV-2026-000001').fill('GN-CONV-E2E-001');
  await page.getByRole('button', { name: "Démarrer l'examen officiel" }).click();
  await expect(page.getByRole('main', { name: 'Examen officiel en cours' })).toBeVisible();
}

test.describe('Examen officiel — résilience runtime', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedCandidate(page);
  });

  test('utilise le temps serveur et autosauvegarde la réponse sans révéler la correction', async ({ page }) => {
    let savedPayload: Record<string, string> | null = null;
    await mockOfficialExam(page, {
      onAutosave: async route => {
        savedPayload = route.request().postDataJSON().answers;
        await route.fulfill({ json: { attempt_id: ATTEMPT_ID, saved: 1, status: 'started' } });
      },
    });

    await openOfficialExam(page);

    await expect(page.getByText('Serveur · synchronisé')).toBeVisible();
    await expect(page.getByText(/19:5\d/)).toBeVisible();

    await page.getByRole('button', { name: /Le véhicule blanc/ }).click();
    await expect.poll(() => savedPayload).toEqual({ 'q-priority-1': 'Le véhicule blanc' });
    await expect(page.getByText('● Réponses sauvegardées')).toBeVisible();

    await expect(page.getByText(/Bonne réponse/i)).toHaveCount(0);
    await expect(page.getByText(/Explication :/i)).toHaveCount(0);
  });

  test('reprend la même tentative après refresh avec réponses et temps conservés', async ({ page }) => {
    let starts = 0;
    await mockOfficialExam(page);
    await page.unroute('**/api/v1/exams/start-from-booking');
    await page.route('**/api/v1/exams/start-from-booking', async route => {
      starts += 1;
      await route.fulfill({ json: { id: ATTEMPT_ID, candidate_id: 'candidate-record-e2e', session_id: 'session-e2e', status: 'started' } });
    });

    await openOfficialExam(page);
    await page.getByRole('button', { name: /Le véhicule blanc/ }).click();
    await expect(page.getByText('Navigation — 1 / 2 répondues')).toBeVisible();

    await page.reload();

    await expect(page.getByRole('main', { name: 'Examen officiel en cours' })).toBeVisible();
    await expect(page.getByText('Navigation — 1 / 2 répondues')).toBeVisible();
    await expect(page.getByText(/19:5\d/)).toBeVisible();
    expect(starts).toBe(1);
  });

  test('conserve une copie locale pendant une coupure puis reprend la sauvegarde serveur', async ({ page }) => {
    let saveAttempt = 0;
    await mockOfficialExam(page, {
      onAutosave: async route => {
        saveAttempt += 1;
        if (saveAttempt === 1) {
          await route.abort('connectionfailed');
          return;
        }
        await route.fulfill({ json: { attempt_id: ATTEMPT_ID, saved: 2, status: 'started' } });
      },
    });

    await openOfficialExam(page);
    await page.getByRole('button', { name: /Le véhicule blanc/ }).click();
    await expect(page.getByText(/Réseau instable — copie locale conservée/)).toBeVisible();

    await page.getByRole('button', { name: /Suivante/ }).click();
    await page.getByRole('button', { name: /^STOP$/ }).click();
    await expect(page.getByText('● Réponses sauvegardées')).toBeVisible();
    expect(saveAttempt).toBe(2);
  });

  test('à 00:00 finalise une seule fois depuis la dernière sauvegarde serveur', async ({ page }) => {
    let timeoutSubmits = 0;
    await mockOfficialExam(page, {
      remainingSeconds: 1,
      onTimeoutSubmit: async route => {
        timeoutSubmits += 1;
        await route.fulfill({
          json: {
            id: ATTEMPT_ID,
            candidate_id: 'candidate-record-e2e',
            session_id: 'session-e2e',
            status: 'submitted',
            score: 1,
            passed: true,
          },
        });
      },
    });

    await openOfficialExam(page);

    await expect(page.getByText('ADMIS')).toBeVisible();
    expect(timeoutSubmits).toBe(1);
    await expect(page.getByText(/Explication de test/)).toBeVisible();
  });
});
