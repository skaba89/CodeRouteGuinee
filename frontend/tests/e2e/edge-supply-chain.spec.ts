import { expect, test, type Page } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

const releaseId = 'release-p9-ui-001';
const artifactSha = 'a'.repeat(64);
const release = {
  release_id: releaseId,
  reference: 'EDGEREL-edge-agent-0.4.0-p9ui',
  status: 'draft', rollout_status: 'draft', rollout_percent: 0,
  canary_node_ids: [], allowed_center_ids: [], rollback_release_id: null,
  manifest: {
    kind: 'center_edge_release_manifest_v1', version: 1, release_id: releaseId,
    software_version: 'edge-agent-0.4.0',
    artifact: { format: 'tar.gz', url: 'https://releases.coderoute.gov.gn/edge-agent-0.4.0.tar.gz', sha256: artifactSha, size_bytes: 123456 },
    created_at: '2026-08-09T05:00:00Z', min_current_version: 'edge-agent-0.3.0', release_notes: 'P9', supply_chain: null,
  },
  manifest_hash: 'b'.repeat(64), manifest_signature_b64: 'sig', signing_key_id: 'edge-release-v1:p9',
};

async function baseMocks(page: Page, role: 'admin' | 'super_admin') {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: role, email: `${role}@dntt.gov.gn`, full_name: role, role, is_active: true }) }));
  await page.route('**/api/v1/auth/csrf-token', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ csrf_token: 'csrf-p9' }) }));
  await page.route('**/api/v1/dashboard/by-center', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ national: { centers_total: 0, centers_active: 0, sessions_total: 0, bookings_total: 0, exams_total: 0, open_incidents_total: 0 }, centers: [] }) }));
  await page.route('**/api/v1/center-edge/fleet', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ generated_at: new Date().toISOString(), status: 'healthy', target_software_version: 'edge-agent-0.4.0', required_capabilities: [], summary: { centers_total: 0, centers_healthy: 0, centers_degraded: 0, centers_critical: 0, centers_without_gateway: 0, nodes_total: 0, nodes_active: 0, nodes_online: 0, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, version_drift_nodes: 0, capability_drift_nodes: 0 }, rollout: { target_version: 'edge-agent-0.4.0', compliant_nodes: 0, upgrade_required_nodes: 0, blocked_nodes: 0 }, centers: [], nodes: [] }) }));
  await page.route('**/api/v1/center-edge/releases', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([release]) }));
}

test('super_admin imports CI evidence matching the draft artifact', async ({ page }) => {
  await baseMocks(page, 'super_admin');
  let attached: Record<string, unknown> | null = null;
  await page.route(`**/api/v1/center-edge/releases/${releaseId}/supply-chain`, async route => {
    attached = JSON.parse(route.request().postData() || '{}');
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ ...release, supply_chain_ready: true, manifest: { ...release.manifest, version: 2, supply_chain: attached } }),
    });
  });

  await page.goto('/#/admin');
  const panel = page.getByTestId('edge-supply-chain-panel');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('Preuve manquante')).toBeVisible();

  const evidence = {
    builder: 'github-actions', source_commit_sha: '1'.repeat(40), workflow_ref: 'Edge Release Supply Chain@refs/tags/edge-agent-0.4.0',
    provenance_url: 'https://github.com/skaba89/CodeRouteGuinee/attestations/1', sbom_sha256: 'c'.repeat(64),
    sbom_attestation_url: 'https://github.com/skaba89/CodeRouteGuinee/attestations/2', subject_sha256: artifactSha,
    vulnerability_scan_status: 'passed',
  };
  await panel.locator('textarea').fill(JSON.stringify(evidence));
  await panel.getByRole('button', { name: 'Rattacher la preuve et re-signer' }).click();
  await expect.poll(() => attached?.subject_sha256).toBe(artifactSha);
  await expect.poll(() => attached?.vulnerability_scan_status).toBe('passed');
});

test('standard admin cannot attach supply chain evidence', async ({ page }) => {
  await baseMocks(page, 'admin');
  await page.goto('/#/admin');
  const panel = page.getByTestId('edge-supply-chain-panel');
  await expect(panel.getByText('Lecture seule')).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Rattacher la preuve et re-signer' })).toHaveCount(0);
  await expect(panel.locator('textarea')).toHaveCount(0);
});
