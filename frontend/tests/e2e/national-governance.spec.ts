import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

const runtime = {
  question_count: 40,
  pass_threshold: 35,
  duration_minutes: 30,
  category_distribution: {
    signalisation: 10, priorites: 6, vitesse: 5, depassement: 5,
    securite_passive: 4, urgence: 4, alcool_drogues: 3, premiers_secours: 3,
  },
  one_attempt_per_session: true,
  retake_cooldown_hours: 0,
};

async function common(page: Page) {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ id: 'admin-dntt-1', email: 'admin@dntt.gov.gn', full_name: 'DNTT', role: 'admin', is_active: true }),
  }));
  await page.route('**/api/v1/dashboard/by-center', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      national: { centers_total: 1, centers_active: 1, sessions_total: 1, bookings_total: 1, exams_total: 1, open_incidents_total: 0 },
      centers: [{ center_id: 'c1', code: 'CRG-001', name: 'Centre DNTT', city: 'Conakry', status: 'accredited', sessions: 1, bookings: 1, exams_total: 1, exams_submitted: 1, exams_passed: 1, pass_rate_pct: 100, open_incidents: 0 }],
    }),
  }));
  await page.route('**/api/v1/center-edge/fleet', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      generated_at: new Date().toISOString(), status: 'healthy', target_software_version: 'edge-agent-0.4.0', required_capabilities: [],
      summary: { centers_total: 1, centers_healthy: 1, centers_degraded: 0, centers_critical: 0, centers_without_gateway: 0, nodes_total: 1, nodes_active: 1, nodes_online: 1, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, version_drift_nodes: 0, capability_drift_nodes: 0 },
      rollout: { target_version: 'edge-agent-0.4.0', compliant_nodes: 1, upgrade_required_nodes: 0, blocked_nodes: 0 },
      centers: [], nodes: [],
    }),
  }));
  await page.route('**/api/v1/center-edge/releases**', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
}

function policy() {
  return {
    id: 'policy-id', reference: 'DNTT-POLICY-OFFICIAL_EXAM_CATEGORY_B-2026.1', authority: 'DNTT',
    title: 'Règles officielles Catégorie B', status: 'active', valid_from: new Date().toISOString(), created_at: new Date().toISOString(), updated_at: null,
    document: {
      kind: 'coderoute_national_exam_policy_v1', schema_version: 1, code: 'OFFICIAL_EXAM_CATEGORY_B', version: '2026.1', parameters: runtime,
      legal_references: [{ reference: 'DNTT-DECISION-2026', title: 'Décision DNTT' }], rationale: 'Validation DNTT', approvals: [
        { actor_id: 'a1', role: 'admin', approved_at: new Date().toISOString(), note: 'ok' },
        { actor_id: 'a2', role: 'super_admin', approved_at: new Date().toISOString(), note: 'ok' },
      ], document_sha256: 'a'.repeat(64), activated_at: new Date().toISOString(), supersedes_reference: null,
    },
  };
}

test('DNTT sees go-live blocked when no national policy is active', async ({ page }) => {
  await common(page);
  await page.route('**/api/v1/national-governance/readiness', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ generated_at: new Date().toISOString(), go_live_allowed: false, active_policy: null, blockers: ['active_policy', 'runtime_alignment', 'official_question_bank'], checks: [
      { code: 'active_policy', required: true, status: 'fail', evidence: null },
      { code: 'runtime_alignment', required: true, status: 'fail', evidence: { reason: 'no_active_policy' } },
      { code: 'official_question_bank', required: true, status: 'fail', evidence: { reason: 'no_active_policy' } },
      { code: 'accredited_centers', required: true, status: 'pass', evidence: { count: 1 } },
    ] }),
  }));
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
  await expect(panel.getByText('DNTT-POLICY-OFFICIAL_EXAM_CATEGORY_B-2026.1')).toBeVisible();
  await expect(panel.getByText('PITR fournisseur')).toBeVisible();
});
