import { expect, test } from '@playwright/test';

test('examen blanc paints the Guinea STOP image with a real visible viewport', async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.removeItem('coderoute:official-exam:active-attempt');
  });

  await page.goto('/#/exam');
  await page.getByRole('button', { name: /commencer un examen blanc/i }).click();

  const frame = page.getByTestId('exam-media-image-frame');
  const viewport = page.getByTestId('exam-media-image-viewport');
  const image = page.getByTestId('exam-media-image');

  await expect(frame).toBeVisible();
  await expect(viewport).toBeVisible();
  await expect(image).toBeVisible();
  await expect(image).toHaveAttribute('src', /\/media\/exam\/guinea\/stop-conakry\.webp$/);

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
