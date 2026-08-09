import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

async function bootstrapAdmin(page: Page) {
  await page.addInitScript((token: string) => {
    localStorage.setItem('coderoute-auth-token', token);
  }, fakeJwt());
  await page.route('**/api/v1/auth/me', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'admin-dntt-1', email: 'admin@dntt.gov.gn', full_name: 'SOC DNTT', role: 'admin', is_active: true,
      }),
    });
  });
  await page.route('**/api/v1/dashboard/by-center', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        national: { centers_total: 0, centers_active: 0, sessions_total: 0, bookings_total: 0, exams_total: 0, open_incidents_total: 0 },
        centers: [],
      }),
    });
  });
  await page.route('**/api/v1/center-edge/fleet', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        generated_at: new Date().toISOString(), status: 'healthy', target_software_version: 'edge-agent-0.4.0', required_capabilities: [],
        summary: { centers_total: 0, centers_healthy: 0, centers_degraded: 0, centers_critical: 0, centers_without_gateway: 0, nodes_total: 0, nodes_active: 0, nodes_online: 0, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, version_drift_nodes: 0, capability_drift_nodes: 0 },
        rollout: { target_version: 'edge-agent-0.4.0', compliant_nodes: 0, upgrade_required_nodes: 0, blocked_nodes: 0 },
        centers: [], nodes: [],
      }),
    });
  });
  await page.route('**/api/v1/center-edge/releases**', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
}

const externalEvidence = [
  'preuve SIEM',
  'preuve OTLP',
  'preuve WAF',
  'tests staging',
  'sign-off',
];

test('DNTT admin sees P11 dormant SOC and blocked national go-live without citizen identity', async ({ page }) => {
  await bootstrapAdmin(page);
  await page.route('**/api/v1/operations/security/status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'disabled',
        generated_at: new Date().toISOString(),
        soc_policy: {
          enabled: false,
          audit_chain_enabled: false,
          audit_verify_interval_seconds: 900,
          otel: { traces_enabled: false, endpoint_configured: false, service_name: 'coderoute-api', sample_ratio: 0.05 },
          waf: { required: false, provider: null },
          siem: { required: false },
        },
        audit_chain: { enabled: false, valid: false, reason: 'disabled' },
        go_live: {
          ready: false,
          controls: [
            { code: 'soc_enabled', passed: false, detail: 'SOC encore dormant' },
            { code: 'audit_hmac_enabled', passed: false, detail: 'AUDIT_CHAIN_ENABLED=false' },
            { code: 'audit_chain_valid', passed: false, detail: 'chaîne audit non validée' },
            { code: 'otel_enabled', passed: false, detail: 'OTLP non activé/configuré' },
            { code: 'waf_enforced', passed: false, detail: 'WAF_REQUIRED/provider non finalisé' },
            { code: 'siem_enforced', passed: false, detail: 'SIEM_REQUIRED=false' },
            { code: 'no_active_security_alert', passed: true, detail: 'aucun signal sécurité actif' },
          ],
          blockers: ['soc_enabled', 'audit_hmac_enabled', 'audit_chain_valid', 'otel_enabled', 'waf_enforced', 'siem_enforced'],
          external_evidence_still_required: externalEvidence,
        },
        signals: { login_failed_15m: 0, login_blocked_15m: 0, login_failed_24h: 2, suspicious_devices: 0, critical_center_incidents: 0 },
        alerts: [],
      }),
    });
  });

  await page.goto('/#/admin');
  const panel = page.getByTestId('national-security-operations');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('SOC national — Security Operations')).toBeVisible();
  await expect(panel.getByText('Non activé')).toBeVisible();
  await expect(panel.getByText('P11 est livré mais volontairement dormant.', { exact: false })).toBeVisible();
  await expect(panel.getByText('OFF', { exact: true })).toBeVisible();
  const gate = page.getByTestId('security-go-live-gate');
  await expect(gate.getByText('Go-live sécurité nationale')).toBeVisible();
  await expect(gate.getByText('Go-live bloqué')).toBeVisible();
  await expect(gate.getByText('soc_enabled', { exact: false })).toBeVisible();
  await expect(gate.getByText('siem_enforced', { exact: false })).toBeVisible();
  await expect(page.getByText('citoyen@example.gn')).toHaveCount(0);
  await expect(page.getByText('98f3be30-a5bf-4a2d-a093-e4a8b7651e4a')).toHaveCount(0);
});

test('DNTT admin sees audit integrity incident and security gate blocked without raw actor details', async ({ page }) => {
  await bootstrapAdmin(page);
  await page.route('**/api/v1/operations/security/status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'critical',
        generated_at: new Date().toISOString(),
        soc_policy: {
          enabled: true,
          audit_chain_enabled: true,
          audit_verify_interval_seconds: 900,
          otel: { traces_enabled: true, endpoint_configured: true, service_name: 'coderoute-api', sample_ratio: 0.05 },
          waf: { required: true, provider: 'institutional-edge' },
          siem: { required: true },
        },
        audit_chain: { enabled: true, valid: false, reason: 'entry_hmac_mismatch', head_seq: 128 },
        go_live: {
          ready: false,
          controls: [
            { code: 'soc_enabled', passed: true, detail: 'SOC_ENABLED=true' },
            { code: 'audit_hmac_enabled', passed: true, detail: 'chaîne HMAC active' },
            { code: 'audit_chain_valid', passed: false, detail: 'chaîne audit non validée' },
            { code: 'otel_enabled', passed: true, detail: 'OTLP actif avec endpoint configuré' },
            { code: 'waf_enforced', passed: true, detail: 'WAF requis via institutional-edge' },
            { code: 'siem_enforced', passed: true, detail: 'SIEM_REQUIRED=true' },
            { code: 'no_active_security_alert', passed: false, detail: '2 signal(aux) sécurité actif(s)' },
          ],
          blockers: ['audit_chain_valid', 'no_active_security_alert'],
          external_evidence_still_required: externalEvidence,
        },
        signals: { login_failed_15m: 12, login_blocked_15m: 1, login_failed_24h: 19, suspicious_devices: 1, critical_center_incidents: 1 },
        alerts: [
          { code: 'AUDIT_CHAIN_INVALID', severity: 'critical' },
          { code: 'AUTH_BRUTE_FORCE_SIGNAL', severity: 'warning' },
        ],
      }),
    });
  });

  await page.goto('/#/admin');
  const panel = page.getByTestId('national-security-operations');
  await expect(panel.getByText('INVALIDE', { exact: true })).toBeVisible();
  await expect(panel.getByText('AUDIT_CHAIN_INVALID')).toBeVisible();
  await expect(panel.getByText('AUTH_BRUTE_FORCE_SIGNAL')).toBeVisible();
  await expect(panel.getByText('OTLP actif')).toBeVisible();
  await expect(panel.getByText('WAF institutional-edge')).toBeVisible();
  const gate = page.getByTestId('security-go-live-gate');
  await expect(gate.getByText('Go-live bloqué')).toBeVisible();
  await expect(gate.getByText('audit_chain_valid', { exact: false })).toBeVisible();
  await expect(gate.getByText('no_active_security_alert', { exact: false })).toBeVisible();
});

test('DNTT admin sees runtime security gate ready only after all P11 controls pass', async ({ page }) => {
  await bootstrapAdmin(page);
  await page.route('**/api/v1/operations/security/status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        generated_at: new Date().toISOString(),
        soc_policy: {
          enabled: true,
          audit_chain_enabled: true,
          audit_verify_interval_seconds: 900,
          otel: { traces_enabled: true, endpoint_configured: true, service_name: 'coderoute-api', sample_ratio: 0.05 },
          waf: { required: true, provider: 'institutional-edge' },
          siem: { required: true },
        },
        audit_chain: { enabled: true, valid: true, reason: null, head_seq: 150 },
        go_live: {
          ready: true,
          controls: [
            { code: 'soc_enabled', passed: true, detail: 'SOC_ENABLED=true' },
            { code: 'audit_hmac_enabled', passed: true, detail: 'chaîne HMAC active' },
            { code: 'audit_chain_valid', passed: true, detail: 'chaîne audit valide' },
            { code: 'otel_enabled', passed: true, detail: 'OTLP actif avec endpoint configuré' },
            { code: 'waf_enforced', passed: true, detail: 'WAF requis via institutional-edge' },
            { code: 'siem_enforced', passed: true, detail: 'SIEM_REQUIRED=true' },
            { code: 'no_active_security_alert', passed: true, detail: 'aucun signal sécurité actif' },
          ],
          blockers: [],
          external_evidence_still_required: externalEvidence,
        },
        signals: { login_failed_15m: 0, login_blocked_15m: 0, login_failed_24h: 1, suspicious_devices: 0, critical_center_incidents: 0 },
        alerts: [],
      }),
    });
  });

  await page.goto('/#/admin');
  const gate = page.getByTestId('security-go-live-gate');
  await expect(gate.getByText('Gate runtime prêt')).toBeVisible();
  await expect(gate.getByText('5 preuve(s) externe(s) restent à archiver', { exact: false })).toBeVisible();
  await expect(gate.getByText('Go-live bloqué')).toHaveCount(0);
});
