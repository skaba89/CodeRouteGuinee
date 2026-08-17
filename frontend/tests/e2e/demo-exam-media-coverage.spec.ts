import { expect, test, type Page } from '@playwright/test';
import { DEMO_QUESTIONS } from '../../src/pages/examQuestions';

const NON_EXPIRED_TEST_JWT = 'eyJhbGciOiJub25lIn0.eyJleHAiOjQxNDI0NDQ4MDB9.signature';

async function openExamAsCandidate(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/me', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'candidate-demo-media-audit',
        email: 'candidate.demo.media@coderoute.test',
        full_name: 'Candidat Audit Media',
        role: 'candidate',
        is_active: true,
        center_id: null,
      }),
    });
  });

  await page.addInitScript(({ token }) => {
    window.localStorage.setItem('coderoute-auth-token', token);
    window.sessionStorage.removeItem('coderoute:official-exam:active-attempt');
  }, { token: NON_EXPIRED_TEST_JWT });

  await page.goto('/#/exam');
  await expect(page.getByRole('button', { name: /commencer un examen blanc/i })).toBeVisible();
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();
}

test('all 40 demo questions keep a renderable media surface', async ({ page }) => {
  test.setTimeout(90_000);
  await openExamAsCandidate(page);

  const next = page.getByRole('button', { name: /suivante/i }).first();

  for (let index = 0; index < DEMO_QUESTIONS.length; index += 1) {
    const question = DEMO_QUESTIONS[index];

    await expect(page.getByText(new RegExp(`QUESTION ${question.number}$`, 'i')).first()).toBeVisible();
    await expect(page.getByText(/illustration indisponible/i)).toHaveCount(0);
    await expect(page.getByText(/panneau non disponible/i)).toHaveCount(0);

    if (question.media_alt) {
      await expect(page.getByText(question.media_alt, { exact: true }).first()).toBeVisible();
    }

    if (index === DEMO_QUESTIONS.length - 1) break;

    await page.keyboard.press('1');
    await expect(next).toBeEnabled();
    await next.click();
  }
});
