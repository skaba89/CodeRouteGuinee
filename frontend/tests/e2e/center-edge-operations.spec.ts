import { expect, test } from '@playwright/test';

// Même origine que Vite pour tester le mode laboratoire sans ajouter un faux
// préflight CORS au mock Playwright. En production, edgeOperatorClient exige HTTPS.
const edgeUrl = 'http://127.0.0.1:4173';
const operatorToken = 'operator-token-that-is-longer-than-32-characters';
const attemptId = 'attempt-center-edge-ops-12345678';

function operatorStatus(status = 'finalized') {
  return {
    node_id: 'node-edge-ratoma',
    center_id: 'center-ratoma',
    software_version: 'edge-agent-0.1.0',
    lease_counts: { [status]: 1 },
    sync_pending: status === 'finalized' ? 1 : 0,
    revalidation_required: 0,
    media_cache: { files: 4, bytes: 2_400_000 },
    leases: [{
      attempt_id: attemptId,
      lease_id: 'lease-ops-1',
      status,
      runtime_state: 'ready',
      deadline_at: new Date(Date.now() + 20 * 60_000).toISOString(),
      duration_ms: 1_800_000,
      elapsed_ms: 300_000,
      question_count: 40,
      event_count: 17,
      claim_state: 'claimed',
      claim_expires_at: Math.floor(Date.now() / 1000) + 300,
      sync_pending: status === 'finalized',
      station: { device_key: 'CRG-STATION-OPS-E2E', label: 'Poste 04', room: 'Salle A' },
      created_at: Date.now() / 1000,
      updated_at: Date.now() / 1000,
    }],
  };
}

test('center operator can supervise, activate and sync through the local Edge gateway', async ({ page }) => {
  let statusValue = 'finalized';
  let activationBody: Record<string, unknown> | null = null;
  let heartbeatCalls = 0;
  let syncCalls = 0;

  await page.route(`${edgeUrl}/health`, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      status: 'ok', node_id: 'node-edge-ratoma', center_id: 'center-ratoma', software_version: 'edge-agent-0.1.0', lease_counts: {},
    }) });
  });
  await page.route(`${edgeUrl}/operator/status`, async route => {
    expect(route.request().headers()['x-edge-operator-token']).toBe(operatorToken);
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(operatorStatus(statusValue)) });
  });
  await page.route(`${edgeUrl}/operator/heartbeat`, async route => {
    heartbeatCalls += 1;
    expect(route.request().headers()['x-edge-operator-token']).toBe(operatorToken);
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ accepted: true }) });
  });
  await page.route(`${edgeUrl}/operator/leases`, async route => {
    activationBody = JSON.parse(route.request().postData() || '{}') as Record<string, unknown>;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      attempt_id: attemptId,
      lease_id: 'lease-ops-new',
      claim_token: 'secret-claim-must-not-be-persisted',
      claim_expires_at: Math.floor(Date.now() / 1000) + 600,
      deadline_at: new Date(Date.now() + 25 * 60_000).toISOString(),
      duration_seconds: 1800,
      question_count: 40,
      candidate_url: `https://frontend.test/#/exam?edge=temporary-candidate-bootstrap`,
      station: { device_key: 'CRG-STATION-OPS-E2E' },
    }) });
  });
  await page.route(`${edgeUrl}/operator/sync/${attemptId}`, async route => {
    syncCalls += 1;
    statusValue = 'synced';
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ accepted: true, attempt_id: attemptId }) });
  });

  await page.goto('/#/center-edge');
  await expect(page.getByRole('heading', { name: 'Console Center Edge' })).toBeVisible();

  await page.getByLabel('URL HTTPS du gateway').fill(edgeUrl);
  await page.getByLabel('Secret opérateur').fill(operatorToken);
  await page.getByRole('button', { name: 'Connecter', exact: true }).click();

  await expect(page.getByText('Session opérateur active', { exact: true })).toBeVisible();
  await expect(page.getByText('EN LIGNE', { exact: true })).toBeVisible();
  await expect(page.getByText('Poste 04', { exact: true })).toBeVisible();
  await expect(page.getByText('À synchroniser', { exact: true }).first()).toBeVisible();

  const storage = await page.evaluate(() => ({
    localToken: localStorage.getItem('coderoute:center-edge:operator-token:v1'),
    sessionToken: sessionStorage.getItem('coderoute:center-edge:operator-token:v1'),
    edgeUrl: localStorage.getItem('coderoute:center-edge:url:v1'),
  }));
  expect(storage.localToken).toBeNull();
  expect(storage.sessionToken).toBe(operatorToken);
  expect(storage.edgeUrl).toBe(edgeUrl);

  await page.getByRole('button', { name: 'Tester la liaison DNTT', exact: true }).click();
  await expect.poll(() => heartbeatCalls).toBe(1);
  await expect(page.getByText('Liaison DNTT centrale confirmée par heartbeat signé.', { exact: true })).toBeVisible();

  await page.getByLabel('ID de tentative officielle').fill(attemptId);
  await page.getByLabel('Poste candidat cible').fill('CRG-STATION-OPS-E2E');
  await page.getByRole('button', { name: 'Précharger et activer', exact: true }).click();
  await expect.poll(() => activationBody?.attempt_id).toBe(attemptId);
  expect(activationBody?.station_device_key).toBe('CRG-STATION-OPS-E2E');
  await expect(page.getByText('Paquet Edge prêt pour le poste', { exact: true })).toBeVisible();
  await expect(page.locator('input[readonly]')).toHaveValue(/temporary-candidate-bootstrap/);

  // Le claim brut reçu du gateway ne doit jamais être persistant dans le navigateur.
  const browserStorageValues = await page.evaluate(() => ({
    local: Object.values(localStorage),
    session: Object.values(sessionStorage),
  }));
  expect(JSON.stringify(browserStorageValues)).not.toContain('secret-claim-must-not-be-persisted');

  await page.getByRole('button', { name: 'Synchroniser', exact: true }).click();
  await expect.poll(() => syncCalls).toBe(1);
  await expect(page.getByText(/synchronisée avec la DNTT/)).toBeVisible();
});
