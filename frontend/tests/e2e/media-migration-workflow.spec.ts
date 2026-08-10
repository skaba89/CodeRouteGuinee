import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

async function auth(page: Page, role: 'admin' | 'super_admin' = 'admin') {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      id: `${role}-1`,
      email: `${role}@coderoute.gn`,
      full_name: 'Opérateur Média',
      role,
      is_active: true,
    }),
  }));
  await page.route('**/api/v1/auth/csrf-token', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ csrf_token: 'e2e-media-csrf-token' }),
  }));
}

async function emptyMediaLibrary(page: Page) {
  await page.route('**/api/v1/media-library/assets**', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, limit: 100, offset: 0 }),
      });
      return;
    }
    await route.fallback();
  });
}

test('migration queue exports an operator CSV and can focus an explicit legacy question', async ({ page }) => {
  await auth(page, 'admin');
  await emptyMediaLibrary(page);

  await page.route('**/api/v1/media-library/migration-queue**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      items: [{
        question_id: 'q-legacy-001',
        category: 'Signalisation',
        text: 'Quel comportement adopter devant ce panneau STOP ?',
        validation_status: 'approved',
        is_active: true,
        queue_state: 'legacy_only',
        priority: 'official_first',
        legacy_media_present: true,
        legacy_media_type: 'sign',
        primary_media: null,
        blocker_codes: [],
        blocker_details: [],
        next_action: 'Associer explicitement un MediaAsset primary validé à cette question.',
      }],
      total: 1,
      matched_questions: 1,
      limit: 200,
      offset: 0,
      state_filter: 'needs_action',
      counts_by_state: { publishable: 0, normalized_blocked: 0, legacy_only: 1, no_media: 0 },
      institutional_validation_inferred: false,
    }),
  }));

  await page.route('**/api/v1/media-library/questions/q-legacy-001', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([]),
  }));

  await page.goto('/#/admin/media-library');
  await page.getByTestId('refresh-media-queue').click();

  const item = page.getByTestId('migration-queue-q-legacy-001');
  await expect(item).toContainText('Legacy à migrer');
  await expect(item).toContainText('Priorité examen officiel');

  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('export-media-queue-csv').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('coderoute-media-migration-needs_action.csv');

  await page.getByTestId('treat-media-question-q-legacy-001').click();
  const focused = page.getByTestId('mapping-focused-question');
  await expect(focused).toBeVisible();
  await expect(focused).toContainText('Quel comportement adopter devant ce panneau STOP ?');
  await expect(page.getByTestId('media-question-mapping')).toContainText('Aucun média normalisé associé à cette question.');
});

test('batch migration imports exported-style CSV and requires successful dry-run before apply', async ({ page }) => {
  await auth(page, 'admin');
  await emptyMediaLibrary(page);
  const dryRunValues: boolean[] = [];

  await page.route('**/api/v1/media-library/migration-plan', async route => {
    const payload = route.request().postDataJSON() as {
      dry_run: boolean;
      replace_existing: boolean;
      reason: string;
      mappings: Array<{ question_id: string; media_id: string }>;
    };
    dryRunValues.push(payload.dry_run);
    expect(payload.replace_existing).toBe(false);
    expect(payload.mappings).toEqual([{ question_id: 'q-001', media_id: 'media-001' }]);
    expect(payload.reason.length).toBeGreaterThanOrEqual(8);

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        dry_run: payload.dry_run,
        replace_existing: false,
        all_ready: true,
        applied: payload.dry_run ? 0 : 1,
        summary: {
          requested: 1,
          ready_create: 1,
          ready_replace: 0,
          no_op: 0,
          blocked: 0,
          missing_question: 0,
          missing_media: 0,
          conflict_existing_primary: 0,
        },
        items: [{
          question_id: 'q-001',
          media_id: 'media-001',
          question_status: 'approved',
          media_type: 'image',
          media_theme: 'STOP',
          status: 'ready_create',
          ready: true,
          blocker_codes: [],
          blocker_details: [],
          existing_primary_media_id: null,
        }],
        institutional_validation_inferred: false,
      }),
    });
  });

  await page.goto('/#/admin/media-library');
  const plan = page.getByTestId('media-migration-plan-input');
  const apply = page.getByTestId('apply-media-migration-plan');
  await expect(apply).toBeDisabled();

  await page.getByTestId('import-media-migration-csv').setInputFiles({
    name: 'migration.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(
      '\uFEFFquestion_id;media_id;queue_state;validation_status;category;text\r\n' +
      '"q-001";"media-001";"legacy_only";"approved";"Signalisation";"Question STOP"\r\n',
      'utf8',
    ),
  });
  await expect(plan).toHaveValue(/q-001.*media-001/);
  await expect(apply).toBeDisabled();

  await page.getByTestId('dry-run-media-migration-plan').click();
  await expect(page.getByText(/Dry-run validé/i)).toBeVisible();
  await expect(page.getByTestId('media-migration-plan-result')).toContainText('ready_create');
  await expect(apply).toBeEnabled();

  await apply.click();
  await expect(page.getByText(/Migration appliquée : 1 association/i)).toBeVisible();
  expect(dryRunValues).toEqual([true, false]);
  await expect(apply).toBeDisabled();
});
