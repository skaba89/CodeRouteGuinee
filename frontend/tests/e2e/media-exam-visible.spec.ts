import { existsSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const NON_EXPIRED_TEST_JWT = 'eyJhbGciOiJub25lIn0.eyJleHAiOjQxMDI0NDQ4MDB9.signature';

async function openExamAsCandidate(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/me', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'candidate-media-e2e',
        email: 'candidate.media@coderoute.test',
        full_name: 'Candidat Media E2E',
        role: 'candidate',
        is_active: true,
        center_id: null,
      }),
    });
  });

  await page.addInitScript(({ token }) => {
    window.localStorage.setItem('coderoute-auth-token', token);
    window.sessionStorage.removeItem('coderoute:official-exam:active-attempt');
  }, { token: NON_EXPIRED_TEST_JWT });

  await page.goto('/#/exam');
  await expect(page.getByRole('button', { name: /commencer un examen blanc/i })).toBeVisible();
}

test('production build contains the Guinea candidate image and video assets', async () => {
  const dist = resolve(process.cwd(), 'dist', 'media', 'exam', 'guinea');
  if (!existsSync(dist)) {
    test.skip(true, 'dist/ absent: this contract is enforced by CI after npm run build');
  }

  const required = [
    'manifest.json',
    'stop-conakry.webp',
    'yield-roundabout-conakry.webp',
    'no-entry-conakry.webp',
    'roundabout-approach-demo.mp4',
  ];
  for (const filename of required) {
    const path = resolve(dist, filename);
    expect(existsSync(path), `${filename} must be copied into the Vite production build`).toBe(true);
    expect(statSync(path).size, `${filename} must not be empty`).toBeGreaterThan(128);
  }
});

test('examen blanc paints the Guinea STOP image with a real visible viewport', async ({ page }) => {
  await openExamAsCandidate(page);
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  const frame = page.getByTestId('exam-media-image-frame');
  const viewport = page.getByTestId('exam-media-image-viewport');
  const image = page.getByTestId('exam-media-image');

  await expect(frame).toBeVisible();
  await expect(viewport).toBeVisible();
  await expect(image).toBeVisible();
  await expect(image).toHaveAttribute('src', /\/media\/exam\/guinea\/stop-conakry\.webp\?v=20260812-1$/);

  const mediaState = await image.evaluate((node: HTMLImageElement) => {
    const style = window.getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return {
      naturalWidth: node.naturalWidth,
      naturalHeight: node.naturalHeight,
      width: rect.width,
      height: rect.height,
      display: style.display,
      visibility: style.visibility,
      opacity: Number(style.opacity),
    };
  });

  expect(mediaState.naturalWidth).toBeGreaterThanOrEqual(1280);
  expect(mediaState.naturalHeight).toBeGreaterThanOrEqual(720);
  expect(mediaState.width).toBeGreaterThan(400);
  expect(mediaState.height).toBeGreaterThan(200);
  expect(mediaState.display).not.toBe('none');
  expect(mediaState.visibility).toBe('visible');
  expect(mediaState.opacity).toBeGreaterThan(0.99);
});

test('examen blanc serves the Guinea roundabout video and paints its fallback on playback failure', async ({ page }) => {
  await openExamAsCandidate(page);
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  const next = page.getByRole('button', { name: /suivante/i }).first();
  for (let index = 0; index < 4; index += 1) {
    await next.click();
  }

  const videoFrame = page.getByTestId('exam-media-video-frame');
  const video = page.getByTestId('exam-media-video');
  await expect(videoFrame).toBeVisible();
  await expect(video).toBeVisible();
  await expect(video).toHaveAttribute('src', /\/media\/exam\/guinea\/roundabout-approach-demo\.mp4\?v=20260812-1$/);
  await expect(video).toHaveAttribute('poster', /\/media\/exam\/guinea\/yield-roundabout-conakry\.webp\?v=20260812-1$/);

  await video.dispatchEvent('error');
  const fallback = page.getByTestId('exam-media-video-fallback');
  await expect(fallback).toBeVisible();
  await expect(fallback).toHaveAttribute('src', /\/media\/exam\/guinea\/yield-roundabout-conakry\.webp\?v=20260812-1$/);
  await expect(page.getByText(/vidéo indisponible — image de secours affichée/i)).toBeVisible();
});
