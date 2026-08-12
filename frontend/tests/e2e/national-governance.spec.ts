import { expect, test } from '@playwright/test';

const runtime = {
  exam_duration_minutes: 30,
  question_count: 40,
  passing_score: 35,
  distribution: {
    signalisation: 12,
    priorites: 6,
    vitesse: 4,
    securite: 8,
    comportement: 4,
    depassement: 3,
    secours: 3,
  },
};

function policy() {
  return {
    id: 'policy-official-exam-b-2026-1',
    policy_code: 'OFFICIAL_EXAM_CATEGORY_B',
    version: '2026.1',
    authority_reference: 'DNTT-POLICY-OFFICIAL_EXAM_CATEGORY_B-2026.1',
    status: 'active',
    effective_from: '2026-01-01T00:00:00Z',
    effective_to: null,
    document: {
      question_count: 40,
      passing_score: 35,
      exam_duration_minutes: 30,
      distribution: runtime.distribution,
    },
    activated_at: '2026-01-01T00:00:00Z',
    created_at: '2025-12-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

async function common(page: Parameters<typeof test>[0] extends never ? never : any) {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: 4_102_444_800 }));
    window.localStorage.setItem('coderoute-auth-token', `e30.${payload}.sig`);
    window.localStorage.setItem('coderoute-refresh-token', 'national-governance-refresh');
  });
  await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'admin-dntt-1', email: 'admin@dntt.gov.gn', full_name: 'Admin DNTT', role: 'super_admin', is_active: true, center_id: null }) }));
  await page.route('**/api/v1/auth/csrf-token', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ csrf_token: 'csrf-national-governance' }) }));
  await page.route('**/api/v1/dashboard*', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total_candidates: 0, verified_candidates: 0, pending_candidates: 0, today_sessions: 0, available_slots: 0, pass_rate: 0, total_revenue_gnf: 0, fraud_alerts: 0, total_centers: 0, active_centers: 0, online_centers: 0, offline_centers: 0, generated_at: new Date().toISOString() }) }));
  await page.route('**/api/v1/operations/summary', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ generated_at: new Date().toISOString(), database_reachable: true, backup_enabled: true, backup_off_region: true, restore_drill_status: 'passed', pitr_provider_status: 'passed', api_failover_status: 'passed', active_incidents: 0 }) }));
  await page.route('**/api/v1/reliability/status', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready', generated_at: new Date().toISOString() }) }));
  await page.route('**/api/v1/security-operations/status', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready', generated_at: new Date().toISOString() }) }));
  await page.route('**/api/v1/national-governance/homologation-evidence-status', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready', generated_at: new Date().toISOString(), complete: true, required: 5, present: 5, missing_codes: [] }) }));
}

test('DNTT sees go-live blocked when no national policy is active', async ({ page }) => {
  await common(page);
  const checks = [{ code: 'active_policy', required: true, status: 'fail', evidence: {} }];
  await page.route('**/api/v1/national-governance/readiness', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ generated_at: new Date().toISOString(), go_live_allowed: false, active_policy: null, blockers: ['Politique DNTT active'], checks }) }));
  await page.route('**/api/v1/national-governance/technical-contract', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ runtime, active_policy: null, alignment: { aligned: false, drift: [{ field: 'active_policy' }] } }) }));
  await page.route('**/api/v1/national-governance/policies', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/national-governance/homologation-dossiers', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));

  await page.goto('/#/admin');
  const panel = page.getByTestId('national-governance-panel');
  await expect(panel).toBeVisible();
  await expect(page.getByTestId('national-go-live-status')).toHaveText('Go-live bloqué');
  await expect(page.getByTestId('homologation-blockers')).toContainText('Politique DNTT active');
  await expect(panel.getByText('Aucune', { exact: true })).toBeVisible();
});

test('DNTT sees homologation eligible when policy and operational evidence are aligned', async ({ page }) => {
  await common(page);
  const active = policy();
  const checks = ['active_policy', 'runtime_alignment', 'official_question_bank', 'accredited_centers', 'backup_off_region', 'restore_drill', 'pitr_provider', 'api_failover']
    .map(code => ({ code, required: true, status: 'pass', evidence: {} }));
  await page.route('**/api/v1/national-governance/readiness', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ generated_at: new Date().toISOString(), go_live_allowed: true, active_policy: active, blockers: [], checks }) }));
  await page.route('**/api/v1/national-governance/technical-contract', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ runtime, active_policy: active, alignment: { aligned: true, runtime, drift: [] } }) }));
  await page.route('**/api/v1/national-governance/policies', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([active]) }));
  await page.route('**/api/v1/national-governance/homologation-dossiers', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));

  await page.goto('/#/admin');
  const panel = page.getByTestId('national-governance-panel');
  await expect(page.getByTestId('national-go-live-status')).toHaveText('Éligible au dossier');
  await expect(panel.getByText('Conforme')).toBeVisible();
  await expect(panel.getByText('40 Q · seuil 35')).toBeVisible();
  await expect(panel.locator('strong').filter({ hasText: /^DNTT-POLICY-OFFICIAL_EXAM_CATEGORY_B-2026\.1$/ })).toBeVisible();
  await expect(panel.getByText('PITR fournisseur')).toBeVisible();
});