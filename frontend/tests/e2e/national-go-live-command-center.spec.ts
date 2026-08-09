import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

async function bootstrap(page: Page) {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: 'admin-1', email: 'admin@dntt.gov.gn', full_name: 'Admin DNTT', role: 'admin', is_active: true }),
  }));
  await page.route('**/api/v1/dashboard/by-center', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ national: { centers_total: 0, centers_active: 0, sessions_total: 0, bookings_total: 0, exams_total: 0, open_incidents_total: 0 }, centers: [] }),
  }));
  await page.route('**/api/v1/center-edge/fleet', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      generated_at: new Date().toISOString(), status: 'healthy', target_software_version: 'edge-agent-0.4.0', required_capabilities: [],
      summary: { centers_total: 0, centers_healthy: 0, centers_degraded: 0, centers_critical: 0, centers_without_gateway: 0, nodes_total: 0, nodes_active: 0, nodes_online: 0, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, version_drift_nodes: 0, capability_drift_nodes: 0 },
      rollout: { target_version: 'edge-agent-0.4.0', compliant_nodes: 0, upgrade_required_nodes: 0, blocked_nodes: 0 }, centers: [], nodes: [],
    }),
  }));
  await page.route('**/api/v1/center-edge/releases**', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/national-governance/technical-contract', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ runtime: {}, active_policy: null, alignment: { aligned: false, drift: [] } }) }));
  await page.route('**/api/v1/national-governance/policies', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/national-governance/homologation-dossiers', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
}

function security(ready: boolean) {
  const controls = [
    'soc_enabled', 'audit_hmac_enabled', 'audit_chain_valid', 'otel_enabled', 'waf_enforced', 'siem_enforced', 'no_active_security_alert',
  ].map(code => ({ code, passed: ready, detail: ready ? 'Contrôle actif' : `${code} non finalisé` }));
  return {
    status: ready ? 'ok' : 'warning', generated_at: new Date().toISOString(),
    soc_policy: {
      enabled: ready, audit_chain_enabled: ready, audit_verify_interval_seconds: 900,
      otel: { traces_enabled: ready, endpoint_configured: ready, service_name: 'coderoute-api', sample_ratio: 0.05 },
      waf: { required: ready, provider: ready ? 'institutional-edge' : null }, siem: { required: ready },
    },
    audit_chain: { enabled: ready, valid: ready, reason: ready ? null : 'disabled' },
    go_live: { ready, controls, blockers: controls.filter(item => !item.passed).map(item => item.code), external_evidence_still_required: ['SIEM', 'OTLP', 'WAF', 'staging', 'sign-off'] },
    signals: { login_failed_15m: 0, login_blocked_15m: 0, login_failed_24h: 0, suspicious_devices: 0, critical_center_incidents: 0 }, alerts: [],
  };
}

function governance(ready: boolean) {
  const codes = ['active_policy', 'runtime_alignment', 'official_question_bank', 'accredited_centers', 'backup_off_region', 'restore_drill', 'pitr_provider', 'api_failover'];
  return {
    generated_at: new Date().toISOString(), go_live_allowed: ready, active_policy: null,
    blockers: ready ? [] : ['active_policy', 'pitr_provider'],
    checks: codes.map(code => ({ code, required: true, status: ready ? 'pass' : (code === 'active_policy' || code === 'pitr_provider') ? 'fail' : 'pass', evidence: {} })),
  };
}

function reliability(ready: boolean) {
  const fresh = new Date().toISOString();
  return {
    generated_at: fresh,
    policy: {
      dr: { rpo_minutes: 5, rto_minutes: 30, backup_required: true, off_region_required: true, primary_region: 'frankfurt', target_region: ready ? 'paris' : null, bucket_configured: ready },
      observability: { metrics_enabled: true, reliability_evidence_enabled: true },
    },
    last_evidence: {
      backup_uploaded: ready ? fresh : null,
      restore_drill_passed: ready ? fresh : null,
      pitr_drill_passed: ready ? fresh : null,
      ha_failover_probe_passed: ready ? fresh : null,
    },
  };
}

async function mockGates(page: Page, ready: boolean) {
  await page.route('**/api/v1/operations/reliability', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(reliability(ready)) }));
  await page.route('**/api/v1/operations/security/status', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(security(ready)) }));
  await page.route('**/api/v1/national-governance/readiness', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(governance(ready)) }));
}

test('command center exposes P10 P11 P12 blockers without claiming institutional approval', async ({ page }) => {
  await bootstrap(page);
  await mockGates(page, false);
  await page.goto('/#/admin');

  const command = page.getByTestId('national-go-live-command-center');
  await expect(command).toBeVisible();
  await expect(command.getByText('Command Center — Go-Live national')).toBeVisible();
  await expect(page.getByTestId('national-automated-readiness')).toContainText('blocker');
  await expect(page.getByTestId('go-live-p10').getByText('BLOQUÉ')).toBeVisible();
  await expect(page.getByTestId('go-live-p11').getByText('BLOQUÉ')).toBeVisible();
  await expect(page.getByTestId('go-live-p12').getByText('BLOQUÉ')).toBeVisible();
  await expect(page.getByTestId('institutional-signoff-required')).toContainText('Décision institutionnelle toujours requise');
});

test('all automated gates can be green while institutional sign-off remains mandatory', async ({ page }) => {
  await bootstrap(page);
  await mockGates(page, true);
  await page.goto('/#/admin');

  const command = page.getByTestId('national-go-live-command-center');
  await expect(page.getByTestId('national-automated-readiness')).toHaveText('Gates automatisables prêts');
  await expect(page.getByTestId('go-live-p10').getByText('PASS')).toBeVisible();
  await expect(page.getByTestId('go-live-p11').getByText('PASS')).toBeVisible();
  await expect(page.getByTestId('go-live-p12').getByText('PASS')).toBeVisible();
  await expect(page.getByTestId('institutional-signoff-required')).toBeVisible();
  await expect(command.getByText('Homologation accordée')).toHaveCount(0);
});
