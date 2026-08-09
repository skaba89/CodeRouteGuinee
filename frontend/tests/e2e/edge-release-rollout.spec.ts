import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

const releaseId = 'release-p8-ui-001';
const nodeId = 'node-canary-ratoma';

const release = {
  release_id: releaseId,
  reference: 'EDGEREL-edge-agent-0.3.1-p8ui',
  status: 'draft',
  rollout_status: 'draft',
  rollout_percent: 0,
  canary_node_ids: [nodeId],
  allowed_center_ids: [],
  rollback_release_id: null,
  manifest: {
    kind: 'center_edge_release_manifest_v1',
    version: 1,
    release_id: releaseId,
    software_version: 'edge-agent-0.3.1',
    artifact: {
      format: 'tar.gz',
      url: 'https://releases.coderoute.gov.gn/edge-agent-0.3.1.tar.gz',
      sha256: 'a'.repeat(64),
      size_bytes: 8_388_608,
    },
    created_at: '2026-08-09T00:00:00Z',
    min_current_version: 'edge-agent-0.3.0',
    release_notes: 'Canary P8 DNTT',
  },
  manifest_hash: 'b'.repeat(64),
  manifest_signature_b64: 'signature',
  signing_key_id: 'edge-release-v1:test',
};

async function mockNationalData(page: Page) {
  await page.route('**/api/v1/dashboard/by-center', async route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      national: { centers_total: 1, centers_active: 1, sessions_total: 1, bookings_total: 4, exams_total: 3, open_incidents_total: 0 },
      centers: [{
        center_id: 'center-ratoma', code: 'RATOMA', name: 'Centre Ratoma', city: 'Conakry', status: 'accredited',
        sessions: 1, bookings: 4, exams_total: 3, exams_submitted: 3, exams_passed: 2, pass_rate_pct: 66.7, open_incidents: 0,
      }],
    }),
  }));
  await page.route('**/api/v1/center-edge/fleet', async route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      generated_at: new Date().toISOString(), status: 'healthy', target_software_version: 'edge-agent-0.3.0',
      required_capabilities: ['release-staging-v1', 'release-attestation-v1'],
      summary: {
        centers_total: 1, centers_healthy: 1, centers_degraded: 0, centers_critical: 0, centers_without_gateway: 0,
        nodes_total: 1, nodes_active: 1, nodes_online: 1, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0,
        version_drift_nodes: 0, capability_drift_nodes: 0,
      },
      rollout: { target_version: 'edge-agent-0.3.0', compliant_nodes: 1, upgrade_required_nodes: 0, blocked_nodes: 0 },
      centers: [{
        center_id: 'center-ratoma', code: 'RATOMA', name: 'Centre Ratoma', city: 'Conakry', health_score: 98,
        health_status: 'healthy', node_count: 1, online_nodes: 1, sync_pending: 0, revalidation_required: 0,
        corrupt_leases: 0, version_drift_nodes: 0, alerts: [],
      }],
      nodes: [{
        node_id: nodeId, reference: 'EDGE-RATOMA-01', center_id: 'center-ratoma', center_code: 'RATOMA', label: 'Gateway Ratoma',
        status: 'active', online: true, capabilities: ['release-staging-v1', 'release-attestation-v1'], last_sequence: 9,
        last_seen_at: new Date().toISOString(), software_version: 'edge-agent-0.3.0', clock_skew_seconds: 1,
        telemetry: { active_leases: 0, finalized_leases: 0, synced_leases: 10, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, media_files: 10, media_bytes: 1000 },
        health_score: 98, health_status: 'healthy', alerts: [], version_drift: false, missing_capabilities: [],
      }],
    }),
  }));
}

test('super_admin can operate signed canary rollout and see attestations', async ({ page }) => {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ id: 'sa-1', email: 'sa@dntt.gov.gn', full_name: 'Super Admin DNTT', role: 'super_admin', is_active: true }),
  }));
  await mockNationalData(page);

  let rolloutBody: Record<string, unknown> | null = null;
  await page.route('**/api/v1/center-edge/releases', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([release]) });
      return;
    }
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(release) });
  });
  await page.route(`**/api/v1/center-edge/releases/${releaseId}/rollout`, async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          release, eligible_nodes: 1,
          attestation_counts: { staged: 0, installed: 1, failed: 0, rolled_back: 0 },
          attestations: [{ attestation_id: 'att-1', node_id: nodeId, center_id: 'center-ratoma', result: 'installed', software_version: 'edge-agent-0.3.1', attested_at: new Date().toISOString() }],
        }),
      });
      return;
    }
    rolloutBody = JSON.parse(route.request().postData() || '{}');
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...release, status: 'canary', rollout_status: 'canary' }) });
  });
  await page.route('**/api/v1/auth/csrf-token', async route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ csrf_token: 'csrf-p8' }),
  }));

  await page.goto('/#/admin');
  const panel = page.getByTestId('edge-release-panel');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('Pilotage super-admin')).toBeVisible();
  await expect(panel.getByText('edge-agent-0.3.1', { exact: true }).first()).toBeVisible();
  await expect(panel.getByText('Gateway Ratoma', { exact: false })).toBeVisible();

  await panel.getByRole('button', { name: 'Canary', exact: true }).click();
  await expect.poll(() => rolloutBody?.rollout_status).toBe('canary');

  await panel.getByRole('button', { name: 'Détails / attestations' }).click();
  await expect(panel.getByText('Installés : 1')).toBeVisible();
  await expect(panel.getByText('installed', { exact: true })).toBeVisible();
});

test('admin sees releases in read-only mode', async ({ page }) => {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ id: 'admin-1', email: 'admin@dntt.gov.gn', full_name: 'Admin DNTT', role: 'admin', is_active: true }),
  }));
  await mockNationalData(page);
  await page.route('**/api/v1/center-edge/releases', async route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify([release]),
  }));

  await page.goto('/#/admin');
  const panel = page.getByTestId('edge-release-panel');
  await expect(panel.getByText('Lecture seule')).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Canary', exact: true })).toHaveCount(0);
  await expect(panel.getByRole('button', { name: 'Créer en draft signé' })).toHaveCount(0);
});
