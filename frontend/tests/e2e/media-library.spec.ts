import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

const baseAsset = {
  id: 'media-001', uuid: 'uuid-media-001', media_type: 'image', usage_type: 'exam',
  storage_provider: 'cloudinary', storage_key: 'coderoute/questions/intersection.webp',
  public_url: null, secure_url: 'https://cdn.example.test/intersection.webp', mime_type: 'image/webp',
  width: 1920, height: 1080, duration_seconds: null, file_size_bytes: 800000,
  checksum_sha256: 'a'.repeat(64), poster_media_id: null, fallback_media_id: null,
  theme: 'PRIORITES', subtheme: 'intersection', country_code: 'GN', regulatory_scope: 'Guinée — examen code de la route',
  source_type: 'licensed', source_reference: 'SOURCE-001', license_type: 'commercial', license_reference: 'GED-LIC-001',
  license_expiration_date: null, copyright_owner: 'Partenaire CodeRoute',
  quality_status: 'draft', regulatory_status: 'not_reviewed', regulatory_authority_reference: null,
  validated_by: null, validated_at: null, created_by: 'creator-1', created_at: new Date().toISOString(), updated_at: new Date().toISOString(), archived_at: null,
};

async function auth(page: Page, role: 'admin' | 'super_admin' | 'candidate') {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: `${role}-1`, email: `${role}@coderoute.gn`, full_name: role === 'candidate' ? 'Candidat Test' : 'Admin Média', role, is_active: true }),
  }));
}

async function mockLibrary(page: Page) {
  let current = { ...baseAsset };
  await page.route('**/api/v1/media-library/assets**', async route => {
    const url = route.request().url();
    const method = route.request().method();
    if (url.includes('/quality-gate')) {
      await route.fulfill({
        status: 200, contentType: 'application/json', body: JSON.stringify({
          media_id: current.id, passed: false, score: current.quality_status === 'validated' ? 80 : 60,
          checks: [{ code: 'CHECKSUM_SHA256', passed: true, detail: 'SHA-256 présent', points: 5, max_points: 5 }],
          blockers: current.quality_status === 'validated' ? ['REGULATORY_APPROVED: regulatory_status=not_reviewed'] : ['PEDAGOGICAL_QUALITY_APPROVED: quality_status=draft'],
          human_review_required: true, institutional_validation_inferred: false,
        }),
      });
      return;
    }
    if (url.includes('/quality/submit') && method === 'POST') {
      current = { ...current, quality_status: 'review_required' };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(current) });
      return;
    }
    if (url.includes('/quality/approve') && method === 'POST') {
      current = { ...current, quality_status: 'validated' };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(current) });
      return;
    }
    if (method === 'GET' && /\/media-library\/assets(?:\?|$)/.test(new URL(url).pathname + new URL(url).search)) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [current], total: 1, limit: 100, offset: 0 }) });
      return;
    }
    await route.fallback();
  });
}

test('admin can open the premium media library and submit an asset for quality review', async ({ page }) => {
  await auth(page, 'admin');
  await mockLibrary(page);
  await page.goto('/#/admin/media-library');

  await expect(page.getByTestId('media-library-page')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Médiathèque CodeRoute Guinée' })).toBeVisible();
  await expect(page.getByText('PRIORITES', { exact: true })).toBeVisible();
  await page.getByTestId('media-card-media-001').click();
  await expect(page.getByTestId('media-quality-gate')).toContainText('60/100');
  await expect(page.getByText('GED-LIC-001', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Soumettre qualité' }).click();
  await expect(page.getByText('Qualité : Revue requise')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Valider qualité' })).toBeVisible();
});

test('candidate cannot access the admin media library route', async ({ page }) => {
  await auth(page, 'candidate');
  await page.goto('/#/admin/media-library');
  await expect(page.getByRole('heading', { name: 'Accès non autorisé' })).toBeVisible();
  await expect(page.getByTestId('media-library-page')).toHaveCount(0);
});

test('super admin sees regulatory approval control only with an authority reference', async ({ page }) => {
  await auth(page, 'super_admin');
  const asset = { ...baseAsset, quality_status: 'validated', regulatory_status: 'under_review' };
  await page.route('**/api/v1/media-library/assets**', async route => {
    if (route.request().url().includes('/quality-gate')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        media_id: asset.id, passed: false, score: 80, checks: [], blockers: ['REGULATORY_APPROVED: under_review'],
        human_review_required: true, institutional_validation_inferred: false,
      }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [asset], total: 1, limit: 100, offset: 0 }) });
  });

  await page.goto('/#/admin/media-library');
  await page.getByTestId('media-card-media-001').click();
  const approve = page.getByTestId('approve-regulatory');
  await expect(approve).toBeDisabled();
  await page.getByTestId('authority-reference').fill('DNTT-MEDIA-2026-0001');
  await expect(approve).toBeEnabled();
  await expect(page.getByText(/ne déclare jamais une homologation institutionnelle automatiquement/i)).toBeVisible();
});
