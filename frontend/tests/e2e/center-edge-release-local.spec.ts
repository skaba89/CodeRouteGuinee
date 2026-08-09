import { expect, test } from '@playwright/test';

const edgeUrl = 'http://127.0.0.1:4173';
const token = 'operator-token-p8-that-is-definitely-longer-than-32-characters';

const stagedState = {
  enabled: true,
  staged: {
    release_id: 'release-local-p8',
    action: 'install',
    software_version: 'edge-agent-0.3.1',
    artifact_sha256: 'a'.repeat(64),
    artifact_size_bytes: 4096,
    verified: true,
  },
  install_receipt: null,
};

test('center operator can check and stage release but browser has no install action', async ({ page }) => {
  let staged = false;
  await page.addInitScript(({ edgeUrl, token }) => {
    localStorage.setItem('coderoute:center-edge:url:v1', edgeUrl);
    sessionStorage.setItem('coderoute:center-edge:operator-token:v1', token);
  }, { edgeUrl, token });

  await page.route('**/health', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ status: 'ok', node_id: 'node-p8', center_id: 'center-p8', software_version: 'edge-agent-0.3.0', lease_counts: {} }),
  }));
  await page.route('**/operator/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      node_id: 'node-p8', center_id: 'center-p8', software_version: 'edge-agent-0.3.0',
      lease_counts: {}, leases: [], sync_pending: 0, revalidation_required: 0,
      media_cache: { files: 0, bytes: 0 }, release: staged ? stagedState : { enabled: true, staged: null, install_receipt: null },
    }),
  }));
  await page.route('**/operator/releases/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify(staged ? stagedState : { enabled: true, staged: null, install_receipt: null }),
  }));
  await page.route('**/operator/releases/check', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      update_available: true,
      action: 'install',
      rollout_status: 'canary',
      release: {
        release_id: 'release-local-p8',
        manifest: {
          software_version: 'edge-agent-0.3.1',
          artifact: { format: 'tar.gz', url: 'https://releases.coderoute.gov.gn/edge-agent-0.3.1.tar.gz', sha256: 'a'.repeat(64), size_bytes: 4096 },
          release_notes: 'Canary local Ratoma',
        },
      },
    }),
  }));
  await page.route('**/operator/releases/stage', async route => {
    staged = true;
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ staged: true, release_id: 'release-local-p8', action: 'install', software_version: 'edge-agent-0.3.1', artifact_sha256: 'a'.repeat(64), artifact_size_bytes: 4096, verified: true }),
    });
  });

  await page.goto('/#/center-edge');
  const panel = page.getByTestId('center-edge-release-local');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('P8 actif')).toBeVisible();

  await panel.getByRole('button', { name: 'Vérifier une mise à jour' }).click();
  await expect(panel.getByText('Release autorisée : edge-agent-0.3.1')).toBeVisible();
  await panel.getByRole('button', { name: 'Précharger et vérifier' }).click();
  await expect(panel.getByText('Artefact vérifié : edge-agent-0.3.1')).toBeVisible();
  await expect(panel.getByText(/apply_verified_release\.py/)).toBeVisible();

  await expect(panel.getByRole('button', { name: /installer/i })).toHaveCount(0);
  await expect(panel.getByRole('button', { name: /exécuter/i })).toHaveCount(0);
});
