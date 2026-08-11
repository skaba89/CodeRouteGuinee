import { expect, test } from '@playwright/test';

const EMAIL = process.env.FULLSTACK_E2E_EMAIL ?? 'e2e.candidate@coderoute.test';
const PASSWORD = process.env.FULLSTACK_E2E_PASSWORD ?? 'FullstackTest123!';
const CENTER = process.env.FULLSTACK_E2E_CENTER ?? 'E2E Centre Kaloum';

/**
 * Ce test n'intercepte AUCUNE requête réseau. Le frontend Vite appelle le vrai
 * backend FastAPI, lui-même connecté au service PostgreSQL du workflow CI.
 */
test('candidate logs in, books a real slot, gets server quote and pays', async ({ page }) => {
  await page.goto('/#/login');

  await page.getByLabel('Adresse email').fill(EMAIL);
  await page.getByLabel('Mot de passe').fill(PASSWORD);
  await page.getByRole('button', { name: /Se connecter/ }).click();

  await expect(page.locator('.topbar-user')).toContainText('Candidat');
  await page.goto('/#/candidate');
  await expect(page.getByRole('heading', { name: 'Mon dossier' })).toBeVisible();

  const centerSelect = page.getByLabel("Choisissez votre centre d'examen");
  await expect(centerSelect).toBeVisible();
  const seededOption = centerSelect.locator('option').filter({ hasText: CENTER });
  await expect(seededOption).toHaveCount(1);
  const centerValue = await seededOption.getAttribute('value');
  expect(centerValue).toBeTruthy();
  await centerSelect.selectOption(centerValue!);

  const reserve = page.getByRole('button', { name: 'Réserver' }).first();
  await expect(reserve).toBeEnabled();
  await reserve.click();

  await expect(page.getByRole('heading', { name: 'Rendez-vous confirmé' })).toBeVisible();
  const bookingReference = page.getByText(/^GN-CONV-\d{4}-\d{6}$/).first();
  await expect(bookingReference).toBeVisible();

  const quote = page.getByTestId('post-booking-server-quote');
  await expect(quote).toContainText('150');
  await expect(quote).toContainText('GNF');
  await expect(quote).not.toContainText('250');

  await page.getByPlaceholder('+224 6XX XX XX XX XX').fill('+224622000099');
  const payButton = page.getByRole('button', { name: /Payer.*150.*000.*GNF/ });
  await expect(payButton).toBeEnabled();
  await payButton.click();

  await expect(page.getByText(/Paiement confirmé — reçu/)).toBeVisible();

  // Validation réseau/DB via l'UI : la liste "Mes réservations" doit être
  // rechargée depuis l'API et la réservation existe réellement côté serveur.
  await page.reload();
  await page.goto('/#/candidate');
  await expect(page.getByText(/^GN-CONV-\d{4}-\d{6}$/).first()).toBeVisible();
});
