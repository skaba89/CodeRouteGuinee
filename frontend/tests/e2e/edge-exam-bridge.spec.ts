import { expect, test, type Route } from '@playwright/test';

const EDGE_ORIGIN = 'https://edge.test:8443';
const FRONTEND_ORIGIN = 'http://127.0.0.1:4173';
const corsHeaders = {
  'access-control-allow-origin': FRONTEND_ORIGIN,
  'access-control-allow-methods': 'GET,POST,OPTIONS',
  'access-control-allow-headers': 'content-type,x-edge-access-token,x-coderoute-station-key',
};

function encodeBootstrap(payload: Record<string, unknown>): string {
  return Buffer.from(JSON.stringify(payload), 'utf8').toString('base64url');
}

async function preflight(route: Route): Promise<boolean> {
  if (route.request().method() !== 'OPTIONS') return false;
  await route.fulfill({ status: 204, headers: corsHeaders });
  return true;
}

test('Edge bootstrap removes the claim from the URL and stores only the candidate session', async ({ page }) => {
  const attemptId = 'attempt-edge-claim-12345678';
  let claimBody: Record<string, unknown> | null = null;

  await page.route(`${EDGE_ORIGIN}/v1/claim`, async route => {
    if (await preflight(route)) return;
    claimBody = JSON.parse(route.request().postData() || '{}') as Record<string, unknown>;
    await route.fulfill({ status: 200, headers: { ...corsHeaders, 'content-type': 'application/json' }, body: JSON.stringify({
      attempt_id: attemptId,
      lease_id: 'lease-edge-1',
      access_token: 'candidate-edge-access-token',
      edge_url: EDGE_ORIGIN,
    }) });
  });

  const encoded = encodeBootstrap({
    edge_url: EDGE_ORIGIN,
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
    return {
      session: raw ? JSON.parse(raw) : null,
      activeAttempt: sessionStorage.getItem('coderoute:official-exam:active-attempt'),
      obsoleteAttempt: sessionStorage.getItem('coderoute:official-exam:active-attempt:v1'),
    };
  }, attemptId);
  expect(stored.session).toMatchObject({ attempt_id: attemptId, edge_url: EDGE_ORIGIN, access_token: 'candidate-edge-access-token' });
  expect(stored.activeAttempt).toBe(attemptId);
  expect(stored.obsoleteAttempt).toBeNull();
  expect(await page.evaluate(() => sessionStorage.getItem('coderoute:edge:pending-bootstrap:v1'))).toBeNull();
  expect(page.url()).not.toContain('claim-token');
});

test('Edge finalization never exposes a local verdict and redirects to DNTT sync pending', async ({ page }) => {
  const attemptId = 'attempt-edge-final-12345678';
  const localAnswers: Record<string, string> = {};
  let finalizeCalls = 0;

  await page.route(`${EDGE_ORIGIN}/v1/exams/${attemptId}/answers`, async route => {
    if (await preflight(route)) return;
    const body = JSON.parse(route.request().postData() || '{}') as { question_id?: string; answer?: string };
    if (body.question_id && body.answer) localAnswers[body.question_id] = body.answer;
    await route.fulfill({ status: 200, headers: { ...corsHeaders, 'content-type': 'application/json' }, body: JSON.stringify({ saved: true, sequence: 1 }) });
  });
  await page.route(`${EDGE_ORIGIN}/v1/exams/${attemptId}/finalize`, async route => {
    if (await preflight(route)) return;
    finalizeCalls += 1;
    await route.fulfill({ status: 200, headers: { ...corsHeaders, 'content-type': 'application/json' }, body: JSON.stringify({ queued_for_sync: true, attempt_id: attemptId }) });
  });
  await page.route(`**/api/v1/exams/${attemptId}/results`, async route => {
    await route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: 'not synchronized yet' }) });
  });

  await page.goto('/#/');
  await page.evaluate(({ id, edgeOrigin }) => {
    sessionStorage.setItem(`coderoute:edge:session:v1:${id}`, JSON.stringify({
      edge_url: edgeOrigin, attempt_id: id, access_token: 'edge-session-token', last_answers: {},
    }));
    sessionStorage.setItem('coderoute:official-exam:active-attempt', id);
  }, { id: attemptId, edgeOrigin: EDGE_ORIGIN });

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
