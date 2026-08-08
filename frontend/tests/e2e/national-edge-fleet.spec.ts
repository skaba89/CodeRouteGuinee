import { expect, test } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

test('DNTT admin sees national Edge health, backlog and rollout', async ({ page }) => {
  await page.addInitScript(token => {
    localStorage.setItem('coderoute-auth-token', token);
  }, fakeJwt());

  await page.route('**/api/v1/auth/me', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'admin-dntt-1',
        email: 'admin@dntt.gov.gn',
        full_name: 'Supervision DNTT',
        role: 'admin',
        is_active: true,
      }),
    });
  });

  await page.route('**/api/v1/dashboard/by-center', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        national: {
          centers_total: 2,
          centers_active: 2,
          sessions_total: 5,
          bookings_total: 80,
          exams_total: 61,
          open_incidents_total: 1,
        },
        centers: [
          {
            center_id: 'center-ratoma', code: 'CRG-RATOMA-001', name: 'Centre Ratoma', city: 'Conakry', status: 'accredited',
            sessions: 3, bookings: 50, exams_total: 40, exams_submitted: 40, exams_passed: 31, pass_rate_pct: 77.5, open_incidents: 0,
          },
          {
            center_id: 'center-kindia', code: 'CRG-KINDIA-001', name: 'Centre Kindia', city: 'Kindia', status: 'accredited',
            sessions: 2, bookings: 30, exams_total: 21, exams_submitted: 20, exams_passed: 12, pass_rate_pct: 60, open_incidents: 1,
          },
        ],
      }),
    });
  });

  await page.route('**/api/v1/center-edge/fleet', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        generated_at: new Date().toISOString(),
        status: 'critical',
        target_software_version: 'edge-agent-0.2.0',
        required_capabilities: ['answer-journal-v1', 'exam-lease-v1', 'fleet-telemetry-v1', 'media-prefetch-v1', 'operator-status-v1'],
        summary: {
          centers_total: 2,
          centers_healthy: 1,
          centers_degraded: 0,
          centers_critical: 1,
          centers_without_gateway: 0,
          nodes_total: 2,
          nodes_active: 2,
          nodes_online: 1,
          sync_pending: 8,
          revalidation_required: 1,
          corrupt_leases: 0,
          version_drift_nodes: 1,
          capability_drift_nodes: 1,
        },
        rollout: {
          target_version: 'edge-agent-0.2.0',
          compliant_nodes: 1,
          upgrade_required_nodes: 1,
          blocked_nodes: 1,
        },
        centers: [
          {
            center_id: 'center-ratoma', code: 'CRG-RATOMA-001', name: 'Centre Ratoma', city: 'Conakry',
            health_score: 95, health_status: 'healthy', node_count: 1, online_nodes: 1,
            sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, version_drift_nodes: 0, alerts: [],
          },
          {
            center_id: 'center-kindia', code: 'CRG-KINDIA-001', name: 'Centre Kindia', city: 'Kindia',
            health_score: 38, health_status: 'critical', node_count: 1, online_nodes: 0,
            sync_pending: 8, revalidation_required: 1, corrupt_leases: 0, version_drift_nodes: 1,
            alerts: ['Aucun gateway Edge en ligne', '8 synchronisation(s) en attente'],
          },
        ],
        nodes: [
          {
            node_id: 'node-ratoma', reference: 'EDGE-RATOMA-01', center_id: 'center-ratoma', center_code: 'CRG-RATOMA-001',
            label: 'Gateway Ratoma', status: 'active', online: true, capabilities: ['answer-journal-v1', 'exam-lease-v1', 'fleet-telemetry-v1', 'media-prefetch-v1', 'operator-status-v1'],
            last_sequence: 91, last_seen_at: new Date().toISOString(), software_version: 'edge-agent-0.2.0', clock_skew_seconds: 1.2,
            telemetry: { active_leases: 2, finalized_leases: 0, synced_leases: 140, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, media_files: 50, media_bytes: 15000000 },
            health_score: 95, health_status: 'healthy', alerts: [], version_drift: false, missing_capabilities: [],
          },
          {
            node_id: 'node-kindia', reference: 'EDGE-KINDIA-01', center_id: 'center-kindia', center_code: 'CRG-KINDIA-001',
            label: 'Gateway Kindia', status: 'active', online: false, capabilities: ['answer-journal-v1', 'exam-lease-v1', 'media-prefetch-v1'],
            last_sequence: 42, last_seen_at: '2026-08-08T20:00:00Z', software_version: 'edge-agent-0.1.0', clock_skew_seconds: 12,
            telemetry: { active_leases: 0, finalized_leases: 8, synced_leases: 70, sync_pending: 8, revalidation_required: 1, corrupt_leases: 0, media_files: 22, media_bytes: 6000000 },
            health_score: 38, health_status: 'critical',
            alerts: [
              { code: 'EDGE_OFFLINE', severity: 'critical', message: 'Aucun heartbeat récent du gateway.' },
              { code: 'EDGE_SYNC_BACKLOG', severity: 'warning', message: '8 tentative(s) finalisée(s) en attente de synchronisation.' },
            ],
            version_drift: true, missing_capabilities: ['fleet-telemetry-v1', 'operator-status-v1'],
          },
        ],
      }),
    });
  });

  await page.goto('/#/admin');

  const fleet = page.getByTestId('national-edge-fleet');
  await expect(fleet).toBeVisible();
  await expect(fleet.getByText('Flotte Center Edge — continuité nationale')).toBeVisible();
  await expect(fleet.getByText('1/2')).toBeVisible();
  await expect(fleet.getByText('8', { exact: true }).first()).toBeVisible();
  await expect(fleet.getByText('edge-agent-0.2.0', { exact: false }).first()).toBeVisible();
  await expect(fleet.getByText('Centre Kindia')).toBeVisible();
  await expect(fleet.getByText('Critique', { exact: true }).first()).toBeVisible();
  await expect(fleet.getByText('8 synchronisation(s) en attente')).toBeVisible();

  await fleet.getByRole('button', { name: 'Voir les gateways' }).click();
  await expect(fleet.getByText('Gateway Ratoma')).toBeVisible();
  await expect(fleet.getByText('Gateway Kindia')).toBeVisible();
  await expect(fleet.getByText('Aucun heartbeat récent du gateway.')).toBeVisible();

  await fleet.getByRole('button', { name: 'Critiques' }).click();
  const centersTable = fleet.locator('table');
  await expect(centersTable.getByText('Centre Kindia')).toBeVisible();
  await expect(centersTable.getByText('Centre Ratoma')).toHaveCount(0);
});
