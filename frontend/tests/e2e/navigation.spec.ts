import { expect, test } from '@playwright/test';

test.describe('CodeRoute Guinee UI smoke tests', () => {
  test('loads national landing page and core navigation', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'CodeRoute Guinee' })).toBeVisible();
    await expect(page.getByText('Produit national pour la Guinee')).toBeVisible();
    await expect(page.getByText('Candidats inscrits')).toBeVisible();

    await page.getByRole('link', { name: 'Candidat' }).click();
    await expect(page.getByRole('heading', { name: 'Dossier, reservation et convocation' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Payer maintenant' })).toBeVisible();

    await page.getByRole('link', { name: 'Centre' }).click();
    await expect(page.getByRole('heading', { name: 'Controle entree centre' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Valider entree' })).toBeDisabled();

    await page.getByRole('link', { name: 'Admin' }).click();
    await expect(page.getByRole('heading', { name: 'Supervision centres, entrees, examens et finances' })).toBeVisible();
    await expect(page.getByText('Decision de pilotage')).toBeVisible();
    await expect(page.getByText('Actions ouvertes')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Dossier de presentation Etat' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Securite et conformite' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Feuille de route institutionnelle' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Exporter le dashboard CSV' })).toBeVisible();

    await page.getByLabel('Navigation principale').getByRole('link', { name: 'Dossier Etat' }).click();
    await expect(page.getByRole('heading', { name: 'Presentation Etat - CodeRoute Guinee' })).toBeVisible();
    await expect(page.getByText('Decision proposee')).toBeVisible();
  });

  test('enforces role based navigation visibility and access denied screen', async ({ page }) => {
    await page.goto('/#/login');

    await page.getByRole('button', { name: 'Candidat' }).click();
    await page.getByRole('link', { name: /Continuer avec ce r(o|ô)le/ }).click();

    await expect(page.getByText('Session : Candidat')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Candidat' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Admin' })).toHaveCount(0);

    await page.goto('/#/admin');
    await expect(page.getByRole('heading', { name: /Page non autoris.e pour ce r.le/ })).toBeVisible();
    await expect(page.getByText(/Le r.le actif/)).toBeVisible();
  });

  test('keeps exam and results screens available for demo flow', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Examen' }).click();
    await expect(page.getByRole('heading', { name: /Question 12 \/ 40/ })).toBeVisible();
    await expect(page.getByText(/Examen s(e|é)curis(e|é)/)).toBeVisible();

    await page.getByRole('link', { name: /R.sultats/ }).click();
    await expect(page.getByRole('heading', { name: 'Releve officiel du code de la route' })).toBeVisible();
    await expect(page.getByText('Suite administrative', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /V.rifier certificat/ })).toBeVisible();
  });
});
