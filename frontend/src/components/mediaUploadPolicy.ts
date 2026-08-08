export type MediaKind = 'image' | 'video';

export type MediaUploadPolicy = {
  resource_type: MediaKind;
  max_bytes: number;
  accepted_mime_types: string[];
  recommended_min_width?: number;
  recommended_min_height?: number;
  recommended_aspect_ratios?: string[];
  delivery_formats?: string[];
  max_duration_seconds?: number;
  delivery_profiles?: string[];
  adaptive_streaming?: boolean;
  poster_required?: boolean;
};

export type MediaInspection = {
  kind: MediaKind;
  sizeBytes: number;
  width?: number;
  height?: number;
  durationSeconds?: number;
  warnings: string[];
};

export const FALLBACK_MEDIA_POLICIES: Record<MediaKind, MediaUploadPolicy> = {
  image: {
    resource_type: 'image',
    max_bytes: 10 * 1024 * 1024,
    accepted_mime_types: ['image/jpeg', 'image/png', 'image/webp', 'image/avif'],
    recommended_min_width: 1280,
    recommended_min_height: 720,
    recommended_aspect_ratios: ['16:9', '4:3', '1:1'],
    delivery_formats: ['avif', 'webp', 'jpeg'],
  },
  video: {
    resource_type: 'video',
    max_bytes: 80 * 1024 * 1024,
    max_duration_seconds: 30,
    accepted_mime_types: ['video/mp4', 'video/webm', 'video/quicktime'],
    recommended_min_width: 1280,
    recommended_min_height: 720,
    recommended_aspect_ratios: ['16:9'],
    delivery_profiles: ['360p', '480p', '720p'],
    adaptive_streaming: true,
    poster_required: true,
  },
};

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 octet';
  const units = ['octets', 'Ko', 'Mo', 'Go'];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`;
}

export function detectMediaKind(file: File): MediaKind {
  const mime = (file.type || '').toLowerCase();
  if (mime.startsWith('image/')) return 'image';
  if (mime.startsWith('video/')) return 'video';

  const name = file.name.toLowerCase();
  if (/\.(jpe?g|png|webp|avif)$/.test(name)) return 'image';
  if (/\.(mp4|webm|mov|qt)$/.test(name)) return 'video';
  throw new Error('Format non reconnu. Utilisez une image JPEG/PNG/WebP/AVIF ou une vidéo MP4/WebM/QuickTime.');
}

function validateBasicFile(file: File, policy: MediaUploadPolicy): void {
  if (file.size <= 0) throw new Error('Le fichier sélectionné est vide.');
  if (file.size > policy.max_bytes) {
    throw new Error(`Fichier trop volumineux : ${formatBytes(file.size)}. Maximum autorisé : ${formatBytes(policy.max_bytes)}.`);
  }

  const mime = (file.type || '').toLowerCase();
  if (mime && !policy.accepted_mime_types.includes(mime)) {
    throw new Error(`Format ${mime} non autorisé. Formats acceptés : ${policy.accepted_mime_types.join(', ')}.`);
  }
}

function inspectImage(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const img = new Image();
    const cleanup = () => URL.revokeObjectURL(objectUrl);
    img.onload = () => {
      const result = { width: img.naturalWidth, height: img.naturalHeight };
      cleanup();
      resolve(result);
    };
    img.onerror = () => {
      cleanup();
      reject(new Error("Impossible de lire l'image. Le fichier peut être corrompu."));
    };
    img.src = objectUrl;
  });
}

function inspectVideo(file: File): Promise<{ width: number; height: number; durationSeconds: number }> {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.muted = true;
    video.playsInline = true;
    const cleanup = () => {
      URL.revokeObjectURL(objectUrl);
      video.removeAttribute('src');
      video.load();
    };
    video.onloadedmetadata = () => {
      const result = {
        width: video.videoWidth,
        height: video.videoHeight,
        durationSeconds: Number.isFinite(video.duration) ? video.duration : 0,
      };
      cleanup();
      resolve(result);
    };
    video.onerror = () => {
      cleanup();
      reject(new Error('Impossible de lire la vidéo. Le fichier peut être corrompu ou utiliser un codec non pris en charge.'));
    };
    video.src = objectUrl;
  });
}

export async function inspectMediaFile(
  file: File,
  kind: MediaKind,
  policy: MediaUploadPolicy,
): Promise<MediaInspection> {
  if (policy.resource_type !== kind) {
    throw new Error(`Politique média incohérente : ${policy.resource_type} reçue pour un fichier ${kind}.`);
  }
  validateBasicFile(file, policy);

  const warnings: string[] = [];
  if (kind === 'image') {
    const dimensions = await inspectImage(file);
    if (
      (policy.recommended_min_width && dimensions.width < policy.recommended_min_width)
      || (policy.recommended_min_height && dimensions.height < policy.recommended_min_height)
    ) {
      warnings.push(
        `Résolution ${dimensions.width}×${dimensions.height} inférieure à la recommandation ${policy.recommended_min_width ?? '—'}×${policy.recommended_min_height ?? '—'}.`,
      );
    }
    return { kind, sizeBytes: file.size, ...dimensions, warnings };
  }

  const metadata = await inspectVideo(file);
  if (policy.max_duration_seconds && metadata.durationSeconds > policy.max_duration_seconds + 0.05) {
    throw new Error(
      `Vidéo trop longue : ${metadata.durationSeconds.toFixed(1)} s. Maximum autorisé : ${policy.max_duration_seconds} s.`,
    );
  }
  if (
    (policy.recommended_min_width && metadata.width < policy.recommended_min_width)
    || (policy.recommended_min_height && metadata.height < policy.recommended_min_height)
  ) {
    warnings.push(
      `Résolution ${metadata.width}×${metadata.height} inférieure à la recommandation ${policy.recommended_min_width ?? '—'}×${policy.recommended_min_height ?? '—'}.`,
    );
  }
  return { kind, sizeBytes: file.size, ...metadata, warnings };
}
