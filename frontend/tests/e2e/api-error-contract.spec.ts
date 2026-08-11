import { expect, test } from '@playwright/test';

import { buildApiError } from '../../src/apiError';

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

test('structured business detail exposes the backend message and code', async () => {
  const error = await buildApiError(jsonResponse({
    detail: {
      code: 'PAYMENT_AMOUNT_MISMATCH',
      message: 'Le montant attendu pour cette réservation est 150000 GNF.',
      expected_amount_gnf: 150000,
    },
  }, 409));

  expect(error.status).toBe(409);
  expect(error.code).toBe('PAYMENT_AMOUNT_MISMATCH');
  expect(error.message).toBe('Le montant attendu pour cette réservation est 150000 GNF.');
  expect(error.message).not.toContain('API error');
});

test('validation errors keep the human message and the failing fields', async () => {
  const error = await buildApiError(jsonResponse({
    detail: 'Données invalides',
    errors: [
      { field: 'body → phone', message: 'Champ requis' },
      { field: 'body → amount_gnf', message: 'La valeur doit être supérieure à 0' },
    ],
  }, 422));

  expect(error.status).toBe(422);
  expect(error.message).toContain('Données invalides');
  expect(error.message).toContain('body → phone : Champ requis');
  expect(error.message).toContain('body → amount_gnf : La valeur doit être supérieure à 0');
  expect(error.validationErrors).toHaveLength(2);
});

test('plain detail strings remain backward compatible', async () => {
  const error = await buildApiError(jsonResponse({ detail: 'Réservation introuvable.' }, 404));

  expect(error.status).toBe(404);
  expect(error.message).toBe('Réservation introuvable.');
  expect(error.code).toBeUndefined();
});

test('malformed or non-json errors fail safely without leaking raw payloads', async () => {
  const response = new Response('<html>proxy failure</html>', {
    status: 502,
    headers: { 'Content-Type': 'text/html' },
  });

  const error = await buildApiError(response);
  expect(error.status).toBe(502);
  expect(error.message).toBe('API error 502');
  expect(error.message).not.toContain('proxy failure');
});
