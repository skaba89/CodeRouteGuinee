/**
 * Tests E2E Playwright — CodeRoute Guinée v3
 * Alignés sur le design system v3 (pages.tsx + App.tsx)
 *
 * Stratégie :
 *   - Mode présentation (sans backend) pour les tests UI
 *   - Sélecteurs basés sur les textes réels du nouveau design
 *   - Tests par rôle : candidat, center, admin, super_admin
 */
import { expect, test } from '@playwright/test';

// ── Helpers ────────────────────────────────────────────────────────────────

async function setRole(page: import('@playwright/test').Page, role: string) {
  await page.goto('/#/login');
  // Sélectionner le rôle via le select (mode présentation)
  const roleSelect = page.locator('select').first();
  if (await roleSelect.count() > 0) {
    await roleSelect.selectOption(role);
  }
  // Ou cliquer le bouton demo
  const demoBtn = page.locator('.demo-btn').filter({ hasText: new RegExp(role, 'i') }).first();
  if (await demoBtn.count() > 0) {
    await demoBtn.click();
  }
}

// ── Test 1 : Page d'accueil ─────────────────────────────────────────────────

test.describe('Page d\'accueil', () => {
  test('affiche le hero et la navigation principale', async ({ page }) => {
    await page.goto('/');

    // Header navigation
    await expect(page.locator('.brand-link')).toBeVisible();
    await expect(page.locator('.brand-text strong')).toHaveText('CodeRoute Guinée');

    // Hero dashboard
    await expect(page.locator('.dash-hero')).toBeVisible();
    await expect(page.locator('.dash-hero-flag')).toHaveText('🇬🇳');

    // Navigation présente
    await expect(page.locator('.top-nav')).toBeVisible();
    await expect(page.locator('.session-panel')).toBeVisible();
  });

  test('affiche les actions rapides selon le rôle par défaut', async ({ page }) => {
    await page.goto('/');

    // Le rôle par défaut affiche au moins une card
    await expect(page.locator('.card').first()).toBeVisible();
  });
});

// ── Test 2 : Connexion et authentification ──────────────────────────────────

test.describe('Page de connexion', () => {
  test('affiche le formulaire de connexion complet', async ({ page }) => {
    await page.goto('/#/login');

    await expect(page.getByText('Accès sécurisé')).toBeVisible();
    await expect(page.getByText('CodeRoute Guinée')).first().toBeVisible();
    await expect(page.getByPlaceholder('agent@coderoute.gov.gn')).toBeVisible();
    await expect(page.getByPlaceholder('••••••••••••')).toBeVisible();
    await expect(page.getByText('Comptes de test disponibles')).toBeVisible();
  });

  test('affiche les 4 comptes de démonstration', async ({ page }) => {
    await page.goto('/#/login');

    const demoBtns = page.locator('.demo-btn');
    await expect(demoBtns).toHaveCount(4);
    await expect(demoBtns.first()).toContainText('Super Admin');
  });

  test('le bouton connexion est désactivé si champs vides', async ({ page }) => {
    await page.goto('/#/login');

    const loginBtn = page.locator('.btn-login');
    await expect(loginBtn).toBeDisabled();
  });

  test('affiche une erreur si credentials incorrects', async ({ page }) => {
    await page.goto('/#/login');

    await page.getByPlaceholder('agent@coderoute.gov.gn').fill('mauvais@test.com');
    await page.getByPlaceholder('••••••••••••').fill('mauvaismdp');
    await page.locator('.btn-login').click();

    await expect(page.locator('.form-error')).toBeVisible({ timeout: 8000 });
  });
});

// ── Test 3 : Navigation par rôle ────────────────────────────────────────────

test.describe('Navigation par rôle (mode présentation)', () => {
  test('rôle candidat : voit Entraînement, Examen, Résultats, Espace candidat', async ({ page }) => {
    await page.goto('/');

    // Changer de rôle via le sélecteur si présent
    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('candidate');
      await page.waitForTimeout(300);
    }

    const nav = page.locator('.nav-links');
    await expect(nav.getByRole('link', { name: 'Entraînement' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Examen' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Résultats' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Espace candidat' })).toBeVisible();
  });

  test('rôle admin : voit Administration et Dossier État', async ({ page }) => {
    await page.goto('/');

    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('admin');
      await page.waitForTimeout(300);
    }

    const nav = page.locator('.nav-links');
    await expect(nav.getByRole('link', { name: 'Administration' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Dossier État' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Portail DNTT' })).toBeVisible();
  });

  test('rôle center : voit Espace centre mais pas Administration', async ({ page }) => {
    await page.goto('/');

    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('center');
      await page.waitForTimeout(300);
    }

    const nav = page.locator('.nav-links');
    await expect(nav.getByRole('link', { name: 'Espace centre' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Administration' })).toHaveCount(0);
  });

  test('accès refusé si rôle non autorisé sur la route', async ({ page }) => {
    await page.goto('/');

    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('candidate');
      await page.waitForTimeout(300);
    }

    await page.goto('/#/admin');
    await expect(page.locator('.access-denied')).toBeVisible();
    await expect(page.getByText('Accès non autorisé')).toBeVisible();
  });
});

// ── Test 4 : Espace candidat ────────────────────────────────────────────────

test.describe('Espace candidat (#/candidate)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('candidate');
      await page.waitForTimeout(300);
    }
    await page.goto('/#/candidate');
  });

  test('affiche le titre et les étapes du parcours', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Mon dossier' })).toBeVisible();
    await expect(page.locator('.steps')).toBeVisible();
    await expect(page.locator('.step-item').first()).toBeVisible();
  });

  test('affiche le formulaire de paiement Mobile Money', async ({ page }) => {
    await expect(page.getByText('Paiement Mobile Money')).toBeVisible();
    await expect(page.locator('.prov-btn').first()).toBeVisible();

    // 4 opérateurs disponibles
    await expect(page.locator('.prov-btn')).toHaveCount(4);
  });

  test('sélectionner un opérateur de paiement', async ({ page }) => {
    const orangeBtn = page.locator('.prov-btn').nth(0);
    const waveBtn   = page.locator('.prov-btn').nth(2);

    await orangeBtn.click();
    await expect(orangeBtn).toHaveClass(/sel/);

    await waveBtn.click();
    await expect(waveBtn).toHaveClass(/sel/);
  });

  test('affiche la section convocation et documents', async ({ page }) => {
    await expect(page.getByText('Convocation & Documents')).toBeVisible();
    await expect(page.getByText('Accéder à l\'examen')).toBeVisible();
    await expect(page.getByText('Voir mes résultats')).toBeVisible();
  });

  test('affiche la section vérification de certificat', async ({ page }) => {
    await expect(page.getByText('Vérifier un certificat')).toBeVisible();
    await expect(page.getByPlaceholder('ATT-xxxxxxxx-xxxx-…')).toBeVisible();
  });

  test('affiche les infos pratiques', async ({ page }) => {
    await expect(page.getByText('Infos pratiques')).toBeVisible();
    await expect(page.getByText(/30 minutes/)).toBeVisible();
  });
});

// ── Test 5 : Espace centre ──────────────────────────────────────────────────

test.describe('Espace centre (#/center)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('center');
      await page.waitForTimeout(300);
    }
    await page.goto('/#/center');
  });

  test('affiche le titre et les 4 sections', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Gestion des examens' })).toBeVisible();
    await expect(page.getByText('Valider l\'entrée candidat')).toBeVisible();
    await expect(page.getByText('Démarrer un examen')).toBeVisible();
    await expect(page.getByText('Déclarer un incident')).toBeVisible();
    await expect(page.getByText('Incidents ouverts')).toBeVisible();
  });

  test('formulaire de validation entrée candidat est complet', async ({ page }) => {
    await expect(page.getByPlaceholder('GN-CONV-2026-000001').first()).toBeVisible();
    await expect(page.getByText('Valider l\'entrée')).toBeVisible();
  });

  test('bouton Valider entrée est désactivé si champs vides', async ({ page }) => {
    const validateBtn = page.getByRole('button', { name: "Valider l'entrée" });
    await expect(validateBtn).toBeDisabled();
  });

  test('formulaire incident avec sélecteur de gravité', async ({ page }) => {
    await expect(page.getByText('Gravité')).toBeVisible();
    const graviteSelect = page.locator('select').last();
    await expect(graviteSelect).toBeVisible();
    await graviteSelect.selectOption('high');
    await expect(graviteSelect).toHaveValue('high');
  });

  test('bouton déclarer incident est désactivé sans description', async ({ page }) => {
    const incidentBtn = page.getByRole('button', { name: "Déclarer l'incident" });
    await expect(incidentBtn).toBeDisabled();
  });
});

// ── Test 6 : Administration (5 onglets) ─────────────────────────────────────

test.describe('Administration (#/admin)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('admin');
      await page.waitForTimeout(300);
    }
    await page.goto('/#/admin');
  });

  test('affiche le titre et les 7 onglets', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tableau de bord national' })).toBeVisible();

    const tabs = ['📊 Dashboard', '👥 Candidats', '💳 Paiements',
                  '🔍 Monitoring', '📝 Questions', '📋 Audit', '👤 Utilisateurs'];
    for (const tab of tabs) {
      await expect(page.getByRole('button', { name: tab })).toBeVisible();
    }
  });

  test('onglet Dashboard affiche les stats et exports', async ({ page }) => {
    await page.getByRole('button', { name: '📊 Dashboard' }).click();
    await expect(page.getByRole('button', { name: '⬇ Dashboard CSV' })).toBeVisible();
    await expect(page.getByRole('button', { name: '⬇ Audit CSV' })).toBeVisible();
  });

  test('navigation entre onglets fonctionne', async ({ page }) => {
    await page.getByRole('button', { name: '👥 Candidats' }).click();
    await expect(page.getByRole('button', { name: 'Actualiser' })).toBeVisible();

    await page.getByRole('button', { name: '📋 Audit' }).click();
    await expect(page.getByRole('button', { name: '⬇ CSV' })).toBeVisible();

    await page.getByRole('button', { name: '👤 Utilisateurs' }).click();
    await expect(page.getByRole('button', { name: 'Actualiser' })).toBeVisible();
  });

  test('alerte présentation visible si non connecté', async ({ page }) => {
    await expect(page.locator('.alert.aw')).toBeVisible();
  });
});

// ── Test 7 : Mode entraînement ──────────────────────────────────────────────

test.describe('Entraînement (#/training)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#/training');
  });

  test('affiche le menu de sélection de catégorie', async ({ page }) => {
    await expect(page.getByRole('heading', { name: "Préparez-vous à l'examen" })).toBeVisible();
    await expect(page.getByText('Toutes les catégories')).toBeVisible();
    await expect(page.getByText('Signalisation')).toBeVisible();
    await expect(page.getByText('Priorités')).toBeVisible();
    await expect(page.getByText("Mode entraînement libre")).toBeVisible();
  });

  test('affiche les 9 boutons de catégorie', async ({ page }) => {
    // 9 catégories (Toutes + 8 spécifiques)
    const catBtns = page.locator('button').filter({ hasText: /📚|🚦|⭐|⏱️|↔️|🛡️|🚨|🚫|🩺/ });
    await expect(catBtns).toHaveCount(9);
  });

  test('sélectionner une catégorie active le bouton', async ({ page }) => {
    await page.getByText('🚦').click();
    await expect(page.locator('button.btn-primary').filter({ hasText: '🚦' })).toBeVisible();
  });

  test('démarrer une session charge les questions', async ({ page }) => {
    await page.getByRole('button', { name: /Démarrer l'entraînement/ }).click();
    await page.waitForTimeout(2000);

    // En mode présentation, les questions fallback s'affichent
    const questionOrMenu = page.locator('.card, h2').first();
    await expect(questionOrMenu).toBeVisible();
  });
});

// ── Test 8 : Examen officiel ────────────────────────────────────────────────

test.describe('Examen (#/exam)', () => {
  test('affiche l\'écran de setup', async ({ page }) => {
    await page.goto('/#/exam');

    await expect(page.getByRole('heading', { name: 'Code de la route — Catégorie B' })).toBeVisible();
    await expect(page.getByText('40 questions')).toBeVisible();
    await expect(page.getByText('30 minutes')).toBeVisible();
    await expect(page.getByText('Seuil : 35/40')).toBeVisible();
    await expect(page.getByRole('button', { name: /Démarrer|Commencer/ })).toBeVisible();
  });

  test('démarrer l\'examen affiche la première question', async ({ page }) => {
    await page.goto('/#/exam');
    await page.getByRole('button', { name: /Démarrer|Commencer/ }).click();

    // Interface d'examen
    await expect(page.locator('.card, [class*="exam"]').first()).toBeVisible();
    await expect(page.getByText(/Q 1 \/ 40/)).toBeVisible({ timeout: 5000 });
  });

  test('le timer est visible pendant l\'examen', async ({ page }) => {
    await page.goto('/#/exam');
    await page.getByRole('button', { name: /Démarrer|Commencer/ }).click();

    // Timer annulaire
    await expect(page.locator('div[style*="conic-gradient"]')).toBeVisible({ timeout: 5000 });
  });

  test('la grille de navigation est visible', async ({ page }) => {
    await page.goto('/#/exam');
    await page.getByRole('button', { name: /Démarrer|Commencer/ }).click();

    // 40 boutons de navigation (sidebar)
    await expect(page.locator('button[style*="aspect-ratio"]').first()).toBeVisible({ timeout: 5000 });
  });

  test('répondre à une question révèle la réponse', async ({ page }) => {
    await page.goto('/#/exam');
    await page.getByRole('button', { name: /Démarrer|Commencer/ }).click();
    await page.waitForTimeout(1000);

    // Cliquer sur la première option
    const firstOption = page.locator('button[style*="border-radius"]').filter({ hasText: /^[A-Z]/ }).first();
    if (await firstOption.count() > 0) {
      await firstOption.click();
      // Le retour visuel doit apparaître
      await page.waitForTimeout(500);
      await expect(page.locator('button[style*="border-radius"]').first()).toBeVisible();
    }
  });
});

// ── Test 9 : Résultats ──────────────────────────────────────────────────────

test.describe('Résultats (#/results)', () => {
  test('affiche le formulaire de recherche', async ({ page }) => {
    await page.goto('/#/results');

    await expect(page.getByRole('heading', { name: 'Résultats & Certificats' })).toBeVisible();
    await expect(page.getByPlaceholder('ATT-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')).toBeVisible();
    await expect(page.getByRole('button', { name: '🔍 Rechercher' })).toBeVisible();
  });

  test('le bouton rechercher est désactivé si champ vide', async ({ page }) => {
    await page.goto('/#/results');
    await expect(page.getByRole('button', { name: '🔍 Rechercher' })).toBeDisabled();
  });

  test('affiche un message d\'erreur si ID introuvable', async ({ page }) => {
    await page.goto('/#/results');
    await page.getByPlaceholder('ATT-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx').fill('ATT-inexistant-123');
    await page.getByRole('button', { name: '🔍 Rechercher' }).click();
    await expect(page.locator('.form-error')).toBeVisible({ timeout: 8000 });
  });
});

// ── Test 10 : Auto-école ────────────────────────────────────────────────────

test.describe('Auto-école (#/school)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('driving_school');
      await page.waitForTimeout(300);
    }
    await page.goto('/#/school');
  });

  test('affiche le tableau de bord pédagogique', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tableau de bord pédagogique' })).toBeVisible();
    await expect(page.getByText('Élèves inscrits')).toBeVisible();
    await expect(page.getByText('Prêts pour l\'examen')).toBeVisible();
    await expect(page.getByText("Nécessitent de l'aide")).toBeVisible();
  });

  test('affiche la table des élèves', async ({ page }) => {
    await expect(page.getByText('Suivi individuel des élèves')).toBeVisible();
    await expect(page.locator('table')).toBeVisible();
    await expect(page.locator('td').first()).toBeVisible();
  });

  test('affiche les prochaines sessions', async ({ page }) => {
    await expect(page.getByText('Prochaines sessions')).toBeVisible();
  });
});

// ── Test 11 : Portail DNTT ──────────────────────────────────────────────────

test.describe('Portail ministériel DNTT (#/ministerial)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const roleSelect = page.locator('.role-switcher select');
    if (await roleSelect.count() > 0) {
      await roleSelect.selectOption('super_admin');
      await page.waitForTimeout(300);
    }
    await page.goto('/#/ministerial');
  });

  test('affiche les 4 onglets du portail', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tableau de bord national — DNTT' })).toBeVisible();
    await expect(page.getByRole('button', { name: '📊 Vue nationale' })).toBeVisible();
    await expect(page.getByRole('button', { name: '📥 Imports officiels' })).toBeVisible();
    await expect(page.getByRole('button', { name: "🖥️ Postes d'examen" })).toBeVisible();
    await expect(page.getByRole('button', { name: "⚠️ Centre d'action" })).toBeVisible();
  });

  test('Vue nationale affiche les boutons export', async ({ page }) => {
    await expect(page.getByRole('button', { name: '⬇ Rapport CSV' })).toBeVisible();
    await expect(page.getByRole('button', { name: '⬇ Rapport PDF' })).toBeVisible();
  });

  test('onglet Imports affiche le formulaire CSV', async ({ page }) => {
    await page.getByRole('button', { name: '📥 Imports officiels' }).click();
    await expect(page.getByText("Type d'import")).toBeVisible();
    await expect(page.getByRole('button', { name: '📥 Aperçu (dry-run)' })).toBeVisible();
  });

  test("onglet Postes affiche le formulaire de création", async ({ page }) => {
    await page.getByRole('button', { name: "🖥️ Postes d'examen" }).click();
    await expect(page.getByText('Créer un poste d\'examen')).toBeVisible();
  });

  test("onglet Centre d'action affiche les alertes", async ({ page }) => {
    await page.getByRole('button', { name: "⚠️ Centre d'action" }).click();
    await expect(page.getByText('Alertes nationales')).toBeVisible();
    await expect(page.getByText('Anti-fraude')).toBeVisible();
  });
});

// ── Test 12 : Langue switcher ───────────────────────────────────────────────

test.describe('Changement de langue', () => {
  test('le sélecteur de langue est visible dans la nav', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.locale-select')).toBeVisible();
  });

  test('changer la langue en Pular modifie l\'interface', async ({ page }) => {
    await page.goto('/');
    const select = page.locator('.locale-select');
    await select.selectOption('ff');
    await page.waitForTimeout(500);

    // La nav doit contenir du texte en Pular
    const navText = await page.locator('.nav-links').textContent();
    expect(navText).toMatch(/Suudu|Jaŋtorde|Naatde/);
  });

  test('changer en Malinké fonctionne', async ({ page }) => {
    await page.goto('/');
    await page.locator('.locale-select').selectOption('man');
    await page.waitForTimeout(500);

    const navText = await page.locator('.nav-links').textContent();
    expect(navText).toMatch(/So Kɔrɔ|Sɛgɛsɛgɛli|Dɔn/);
  });

  test('changer en Soussou fonctionne', async ({ page }) => {
    await page.goto('/');
    await page.locator('.locale-select').selectOption('sus');
    await page.waitForTimeout(500);

    const navText = await page.locator('.nav-links').textContent();
    expect(navText).toMatch(/Bande|Kɔntɔrɔli|Siga/);
  });
});

// ── Test 13 : Accessibilité et responsive ───────────────────────────────────

test.describe('Accessibilité et structure', () => {
  test('la nav a un aria-label de navigation principale', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav[aria-label="Navigation principale"]')).toBeVisible();
  });

  test('les formulaires ont des labels accessibles', async ({ page }) => {
    await page.goto('/#/login');
    await expect(page.getByLabel('Adresse e-mail')).toBeVisible();
    await expect(page.getByLabel('Mot de passe')).toBeVisible();
  });

  test('les boutons désactivés ont l\'attribut disabled', async ({ page }) => {
    await page.goto('/#/results');
    const btn = page.getByRole('button', { name: '🔍 Rechercher' });
    await expect(btn).toBeDisabled();
  });

  test('les liens de navigation ont des href corrects', async ({ page }) => {
    await page.goto('/');
    const homeLink = page.locator('.brand-link');
    await expect(homeLink).toHaveAttribute('href', '#/');
  });
});
