import { existsSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const NON_EXPIRED_TEST_JWT = 'eyJhbGciOiJub25lIn0.eyJleHAiOjQxMDI0NDQ4MDB9.signature';
const GUINEA_MEDIA_VERSION = '20260817-1';

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

async function expectCandidateVisibleStop(page: Page): Promise<'image' | 'fallback'> {
  const image = page.getByTestId('exam-media-image');
  const fallback = page.getByTestId('exam-media-image-fallback');

  // The image element can exist while still hidden during pixel validation.
  // Wait for one stable visible terminal state instead of racing on DOM count.
  await expect.poll(async () => (await image.isVisible()) || (await fallback.isVisible())).toBe(true);

  if (await fallback.isVisible()) {
    await expect(page.getByRole('img', { name: /stop/i })).toBeVisible();
    await expect(page.getByText(/image indisponible — panneau de secours affiché/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /afficher l'image en plein écran/i })).toHaveCount(0);
    return 'fallback';
  }

  await expect(image).toBeVisible();
  await expect(image).toHaveCSS('opacity', '1');
  await expect(image).toHaveAttribute('src', new RegExp(`/media/exam/guinea/stop-conakry\\.webp\\?v=${GUINEA_MEDIA_VERSION}(?:&retry=\\d+)?$`));

  const pixelState = await image.evaluate((node: HTMLImageElement) => {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 18;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    let minLuma = 255;
    let maxLuma = 0;
    let chromaticPixels = 0;
    if (context) {
      context.drawImage(node, 0, 0, canvas.width, canvas.height);
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index + 3] < 32) continue;
        const red = pixels[index];
        const green = pixels[index + 1];
        const blue = pixels[index + 2];
        const luma = Math.round(0.2126 * red + 0.7152 * green + 0.0722 * blue);
        minLuma = Math.min(minLuma, luma);
        maxLuma = Math.max(maxLuma, luma);
        if (Math.max(red, green, blue) - Math.min(red, green, blue) >= 16) chromaticPixels += 1;
      }
    }
    return {
      naturalWidth: node.naturalWidth,
      naturalHeight: node.naturalHeight,
      lumaRange: maxLuma - minLuma,
      maxLuma,
      chromaticPixels,
    };
  });

  expect(pixelState.naturalWidth).toBeGreaterThanOrEqual(320);
  expect(pixelState.naturalHeight).toBeGreaterThanOrEqual(180);
  expect(pixelState.lumaRange).toBeGreaterThanOrEqual(18);
  expect(pixelState.maxLuma >= 48 || pixelState.chromaticPixels >= 8).toBe(true);
  return 'image';
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

test('examen blanc always paints a meaningful STOP visual for the candidate', async ({ page }) => {
  await openExamAsCandidate(page);
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  await expect(page.getByTestId('exam-media-image-frame')).toBeVisible();
  await expect(page.getByTestId('exam-media-image-viewport')).toBeVisible();
  await expectCandidateVisibleStop(page);
});

test('examen blanc replaces a technically loaded but visually blank STOP image with the semantic fallback', async ({ page }) => {
  await page.route('**/media/exam/guinea/stop-conakry.webp**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#0d2137"/></svg>',
    });
  });

  await openExamAsCandidate(page);
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  expect(await expectCandidateVisibleStop(page)).toBe('fallback');
});

test('examen blanc retries a failed STOP request without ever returning to an empty panel', async ({ page }) => {
  let stopRequests = 0;
  await page.route('**/media/exam/guinea/stop-conakry.webp**', async route => {
    stopRequests += 1;
    if (stopRequests === 1) {
      await route.abort('failed');
      return;
    }
    await route.continue();
  });

  await openExamAsCandidate(page);
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  await expect(page.getByTestId('exam-media-image-fallback')).toBeVisible();
  await page.getByRole('button', { name: /réessayer/i }).click();
  await expect.poll(() => stopRequests).toBeGreaterThanOrEqual(2);
  await expectCandidateVisibleStop(page);
});

test('examen blanc serves the Guinea roundabout video and paints its fallback on playback failure', async ({ page }) => {
  await openExamAsCandidate(page);
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  const next = page.getByRole('button', { name: /suivante/i }).first();
  for (let index = 0; index < 4; index += 1) {
    await page.keyboard.press('1');
    await expect(next).toBeEnabled();
    await next.click();
  }

  const videoFrame = page.getByTestId('exam-media-video-frame');
  const video = page.getByTestId('exam-media-video');
  await expect(videoFrame).toBeVisible();
  await expect(video).toBeVisible();
  await expect(video).toHaveAttribute('src', new RegExp(`/media/exam/guinea/roundabout-approach-demo\\.mp4\\?v=${GUINEA_MEDIA_VERSION}$`));
  await expect(video).toHaveAttribute('poster', new RegExp(`/media/exam/guinea/yield-roundabout-conakry\\.webp\\?v=${GUINEA_MEDIA_VERSION}$`));

  await video.dispatchEvent('error');
  const fallback = page.getByTestId('exam-media-video-fallback');
  await expect(fallback).toBeVisible();
  await expect(fallback).toHaveAttribute('src', new RegExp(`/media/exam/guinea/yield-roundabout-conakry\\.webp\\?v=${GUINEA_MEDIA_VERSION}$`));
  await expect(page.getByText(/vidéo indisponible — image de secours affichée/i)).toBeVisible();
});
