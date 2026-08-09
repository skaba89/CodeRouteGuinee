import { expect, test } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

async function bootstrapAdmin(page: Parameters<typeof test>[0] extends never ? never : any) {
  await page.addInitScript((token: string) => {
    localStorage.setItem('coderoute-auth-token', token);
  }, fakeJwt());
  await page.route('**/api/v1/auth/me', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'admin-dntt-1', email: 'admin@dntt.gov.gn', full_name: 'SOC DNTT', role: 'admin', is_active: true,
      }),
    });
  });
  await page.route('**/api/v1/dashboard/by-center', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        national: { centers_total: 0, centers_active: 0, sessions_total: 0, bookings_total: 0, exams_total: 0, open_incidents_total: 0 },
        centers: [],
      }),
    });
  });
  await page.route('**/api/v1/center-edge/fleet', async (route: any) => {
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
  await page.route('**/api/v1/center-edge/releases**', async (route: any) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
}

test('DNTT admin sees P11 dormant SOC state without citizen identity', async ({ page }) => {
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
  await expect(page.getByText('citoyen@example.gn')).toHaveCount(0);
  await expect(page.getByText('98f3be30-a5bf-4a2d-a093-e4a8b7651e4a')).toHaveCount(0);
});

test('DNTT admin sees audit integrity incident without raw actor details', async ({ page }) => {
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
});
