import { expect, test } from '@playwright/test';

const NON_EXPIRED_TEST_JWT = 'eyJhbGciOiJub25lIn0.eyJleHAiOjQxMDI0NDQ4MDB9.signature';

test('examen blanc affiche une question à la fois et exige une réponse avant Suivante', async ({ page }) => {
  await page.addInitScript(({ token }) => {
    window.localStorage.setItem('coderoute-auth-token', token);
    window.localStorage.setItem('coderoute-refresh-token', 'demo-sequential-refresh');
    window.sessionStorage.removeItem('coderoute:official-exam:active-attempt');
  }, { token: NON_EXPIRED_TEST_JWT });

  await page.route('**/api/v1/auth/me', route => route.fulfill({
    json: {
      id: 'candidate-demo-sequential',
      email: 'candidate.demo.sequential@coderoute.test',
      full_name: 'Candidat Démo Séquentiel',
      role: 'candidate',
      is_active: true,
      center_id: null,
    },
  }));
  await page.route('**/api/v1/auth/csrf-token', route => route.fulfill({ json: { csrf_token: 'csrf-demo-sequential' } }));

  await page.goto('/#/exam');
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  await expect(page.getByRole('main', { name: 'Examen blanc en cours' })).toBeVisible();
  await expect(page.getByLabel(/Question 1 sur 40/)).toBeVisible();
  await expect(page.getByText(/Navigation —/)).toHaveCount(0);

  const next = page.getByRole('button', { name: /Suivante/ });
  await expect(next).toBeDisabled();

  await page.keyboard.press('ArrowRight');
  await expect(page.getByLabel(/Question 1 sur 40/)).toBeVisible();

  await page.keyboard.press('1');
  await expect(next).toBeEnabled();
  await next.click();

  await expect(page.getByLabel(/Question 2 sur 40/)).toBeVisible();
});
