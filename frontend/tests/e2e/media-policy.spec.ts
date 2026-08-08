import { expect, test } from '@playwright/test';
import {
  FALLBACK_MEDIA_POLICIES,
  detectMediaKind,
  formatBytes,
  inspectMediaFile,
} from '../../src/components/mediaUploadPolicy';

function fakeFile(name: string, type: string, size: number): File {
  return { name, type, size } as File;
}

test.describe('Media Factory — validation pré-upload', () => {
  test('détecte image et vidéo à partir du MIME', () => {
    expect(detectMediaKind(fakeFile('route.webp', 'image/webp', 1024))).toBe('image');
    expect(detectMediaKind(fakeFile('carrefour.mp4', 'video/mp4', 1024))).toBe('video');
  });

  test('utilise aussi l’extension quand le navigateur ne fournit pas de MIME', () => {
    expect(detectMediaKind(fakeFile('route.AVIF', '', 1024))).toBe('image');
    expect(detectMediaKind(fakeFile('carrefour.WEBM', '', 1024))).toBe('video');
  });

  test('refuse un format inconnu avant tout upload', () => {
    expect(() => detectMediaKind(fakeFile('question.pdf', 'application/pdf', 1024))).toThrow(/Format non reconnu/);
  });

  test('refuse une image supérieure à 10 Mo avant lecture du fichier', async () => {
    const oversized = fakeFile(
      'route.jpg',
      'image/jpeg',
      FALLBACK_MEDIA_POLICIES.image.max_bytes + 1,
    );
    await expect(inspectMediaFile(oversized, 'image', FALLBACK_MEDIA_POLICIES.image)).rejects.toThrow(/trop volumineux/);
  });

  test('refuse une vidéo supérieure à 80 Mo avant lecture du fichier', async () => {
    const oversized = fakeFile(
      'scene.mp4',
      'video/mp4',
      FALLBACK_MEDIA_POLICIES.video.max_bytes + 1,
    );
    await expect(inspectMediaFile(oversized, 'video', FALLBACK_MEDIA_POLICIES.video)).rejects.toThrow(/trop volumineux/);
  });

  test('refuse un MIME non autorisé même si le type image/vidéo est reconnaissable', async () => {
    const svg = fakeFile('panneau.svg', 'image/svg+xml', 2048);
    await expect(inspectMediaFile(svg, 'image', FALLBACK_MEDIA_POLICIES.image)).rejects.toThrow(/non autorisé/);
  });

  test('formate les tailles de manière lisible pour l’admin', () => {
    expect(formatBytes(10 * 1024 * 1024)).toBe('10 Mo');
    expect(formatBytes(1536)).toBe('1.5 Ko');
  });
});
