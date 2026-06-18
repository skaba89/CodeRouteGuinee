import { expect, test } from '@playwright/test';

test.describe('CodeRoute Guinee UI smoke tests', () => {
  test('loads national landing page and core navigation', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'CodeRoute Guinee' })).toBeVisible();
    await expect(page.getByText('Produit national pour la Guinee')).toBeVisible();
    await expect(page.getByText('Candidats inscrits')).toBeVisible();

    await page.getByRole('link', { name: 'Candidat' }).click();
    await expect(page.getByRole('heading', { name: 'Dossier, reservation et convocation' })).toBeVisible();
    await expect(page.getByText('Dossier recevable')).toBeVisible();
    await expect(page.getByText('Avant la session', { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Pieces justificatives' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deposer la piece' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Recours et reclamations' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Deposer le recours' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Payer maintenant' })).toBeVisible();

    await page.getByRole('link', { name: 'Centre' }).click();
    await expect(page.getByRole('heading', { name: 'Controle entree centre' })).toBeVisible();
    await expect(page.locator('input[value="CRG-BOOK-DEMO-001"]')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Valider entree' })).toBeEnabled();
    await expect(page.getByRole('heading', { name: 'Declaration incident' })).toBeVisible();
    await expect(page.getByText(/Mode presentation : declaration officielle reservee/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Declarer incident' })).toBeDisabled();

    await page.getByRole('link', { name: 'Admin' }).click();
    await expect(page.getByRole('heading', { name: 'Supervision centres, entrees, examens et finances' })).toBeVisible();
    await expect(page.getByText('Decision de pilotage')).toBeVisible();
    await expect(page.getByText('Actions ouvertes')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Incidents' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Importer candidats officiels' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Importer centres officiels' })).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Incidents centres et reprises' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Actualiser' })).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Verification identite candidat' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Filtrer les pieces' })).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Recours et reclamations candidats' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Importer questions officielles' })).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Dossier de presentation Etat' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Securite et conformite' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Preparation production' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Feuille de route institutionnelle' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Exporter le dashboard CSV' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Exporter dossier Etat PDF' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Monitoring examen et alertes fraude' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Charger monitoring' })).toBeDisabled();

    await page.getByLabel('Navigation principale').getByRole('link', { name: 'Dossier Etat' }).click();
    await expect(page.getByRole('heading', { name: 'Presentation Etat - CodeRoute Guinee' })).toBeVisible();
    await expect(page.getByText('Decision proposee')).toBeVisible();
  });

  test('enforces role based navigation visibility and access denied screen', async ({ page }) => {
    await page.goto('/#/login');

    await page.getByRole('button', { name: 'Candidat' }).click();
    await page.getByRole('link', { name: /Continuer avec ce r.le/ }).click();

    await expect(page.getByText('Presentation : Candidat')).toBeVisible();
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
    await expect(page.getByText(/Examen s.curis./)).toBeVisible();
    await page.getByRole('button', { name: 'Question suivante' }).click();
    await expect(page.getByRole('heading', { name: /Question 13 \/ 40/ })).toBeVisible();
    await page.getByRole('button', { name: /La priorite a droite/ }).click();
    await expect(page.getByText('2 reponse(s) saisie(s)')).toBeVisible();
    await expect(page.getByText(/Mode presentation : les questions restent navigables/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Demarrer tentative API' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Soumettre les reponses' })).toBeDisabled();

    await page.getByRole('link', { name: /R.sultats/ }).click();
    await expect(page.getByRole('heading', { name: 'Releve officiel du code de la route' })).toBeVisible();
    await expect(page.getByText('Suite administrative', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /V.rifier certificat/ })).toBeVisible();
  });
});
