import { expect, test } from '@playwright/test';

function encodeBootstrap(payload: Record<string, unknown>): string {
  return Buffer.from(JSON.stringify(payload), 'utf8').toString('base64url');
}

test('Edge bootstrap removes the claim from the URL and stores only the candidate session', async ({ page }) => {
  const attemptId = 'attempt-edge-claim-12345678';
  let claimBody: Record<string, unknown> | null = null;

  await page.route('https://edge.test:8443/v1/claim', async route => {
    claimBody = JSON.parse(route.request().postData() || '{}') as Record<string, unknown>;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      attempt_id: attemptId,
      lease_id: 'lease-edge-1',
      access_token: 'candidate-edge-access-token',
      edge_url: 'https://edge.test:8443',
    }) });
  });

  const encoded = encodeBootstrap({
    edge_url: 'https://edge.test:8443',
    attempt_id: attemptId,
    claim_token: 'claim-token-abcdefghijklmnopqrstuvwxyz-1234567890',
    claim_expires_at: Math.floor(Date.now() / 1000) + 600,
  });

  await page.goto(`/#/exam?edge=${encoded}`);
  await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#/exam');
  await expect.poll(() => claimBody?.attempt_id).toBe(attemptId);
  expect(String(claimBody?.station_device_key || '')).toMatch(/^CRG-STATION-/);

  const stored = await page.evaluate(id => {
    const raw = sessionStorage.getItem(`coderoute:edge:session:v1:${id}`);
    return raw ? JSON.parse(raw) : null;
  }, attemptId);
  expect(stored).toMatchObject({ attempt_id: attemptId, edge_url: 'https://edge.test:8443', access_token: 'candidate-edge-access-token' });
  expect(await page.evaluate(() => sessionStorage.getItem('coderoute:edge:pending-bootstrap:v1'))).toBeNull();
  expect(page.url()).not.toContain('claim-token');
});

test('Edge finalization never exposes a local verdict and redirects to DNTT sync pending', async ({ page }) => {
  const attemptId = 'attempt-edge-final-12345678';
  const localAnswers: Record<string, string> = {};
  let finalizeCalls = 0;

  await page.route(`https://edge.test:8443/v1/exams/${attemptId}/answers`, async route => {
    const body = JSON.parse(route.request().postData() || '{}') as { question_id?: string; answer?: string };
    if (body.question_id && body.answer) localAnswers[body.question_id] = body.answer;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ saved: true, sequence: 1 }) });
  });
  await page.route(`https://edge.test:8443/v1/exams/${attemptId}/finalize`, async route => {
    finalizeCalls += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ queued_for_sync: true, attempt_id: attemptId }) });
  });
  await page.route(`**/api/v1/exams/${attemptId}/results`, async route => {
    await route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: 'not synchronized yet' }) });
  });

  await page.goto('/#/');
  await page.evaluate(id => {
    sessionStorage.setItem(`coderoute:edge:session:v1:${id}`, JSON.stringify({
      edge_url: 'https://edge.test:8443', attempt_id: id, access_token: 'edge-session-token', last_answers: {},
    }));
  }, attemptId);

  const responseStatus = await page.evaluate(async id => {
    const response = await fetch(`/api/v1/exams/${id}/submit`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ answers: { q1: 'A' } }),
    });
    return response.status;
  }, attemptId);

  expect(responseStatus).toBe(200);
  await expect.poll(() => finalizeCalls).toBe(1);
  expect(localAnswers).toEqual({ q1: 'A' });
  await expect(page).toHaveURL(/#\/edge-pending$/);
  await expect(page.getByRole('heading', { name: 'Résultat officiel en attente de synchronisation DNTT' })).toBeVisible();
  await expect(page.getByText(/Aucun score ni verdict n'est calculé sur ce poste/i)).toBeVisible();
  await expect(page.getByText(/^ADMIS$/)).toHaveCount(0);
  await expect(page.getByText(/^AJOURNÉ$/)).toHaveCount(0);
});
