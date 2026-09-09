import { MediaBlock as PremiumMediaBlock, VideoPlayer } from './ExamMediaPremium';

function deriveCloudinaryPoster(url: string): string | undefined {
  try {
    const parsed = new URL(url);
    if (parsed.hostname !== 'res.cloudinary.com' || !parsed.pathname.includes('/video/upload/')) return undefined;
    return `${parsed.origin}${parsed.pathname.replace(/\.[a-z0-9]+$/i, '.jpg')}`;
  } catch {
    return undefined;
  }
}

/**
 * Force Cloudinary to negotiate a browser-compatible delivery format.
 *
 * Uploads can legitimately arrive as MOV/WebM while the exam player must work
 * consistently on Chrome, Safari and iOS. Cloudinary's f_auto transformation
 * selects a supported delivery format for the requesting browser; q_auto also
 * keeps the mobile data budget reasonable. The original MediaAsset URL and
 * metadata remain untouched — this is a delivery-only transformation.
 *
 * Signed delivery URLs are left untouched because injecting a transformation
 * would invalidate their signature. CodeRoute uploads currently use public
 * Cloudinary delivery URLs, but failing closed here avoids a future regression.
 */
function normalizeCloudinaryVideoDelivery(url: string): string {
  try {
    const parsed = new URL(url);
    const marker = '/video/upload/';
    if (parsed.hostname !== 'res.cloudinary.com' || !parsed.pathname.includes(marker)) return url;

    const suffix = parsed.pathname.split(marker, 2)[1] ?? '';
    if (suffix.startsWith('s--')) return url;

    // Avoid stacking the same optimization when an upstream service already
    // supplied it. Other transformations can safely remain after this step.
    if (parsed.pathname.includes(`${marker}f_auto`) || parsed.pathname.includes(`${marker}q_auto,f_auto`)) {
      return url;
    }

    parsed.pathname = parsed.pathname.replace(marker, `${marker}f_auto,q_auto/`);
    return parsed.toString();
  } catch {
    return url;
  }
}

function isPlayableUrl(url: string): boolean {
  return /^https?:\/\//i.test(url) || url.startsWith('/media/');
}

function normalizeLegacySymbolicMedia(mediaType?: string, media?: string): string | undefined {
  if (mediaType === 'scene' && media === 'situation_overtake_forbidden') {
    return 'situation_overtake';
  }
  return media;
}

export type ExamMediaRuntimeProps = {
  mediaType?: string;
  media?: string;
  alt?: string;
  poster?: string;
  fallback?: string;
};

/**
 * Runtime media facade used by exam screens.
 *
 * The backend already returns the validated poster/fallback attached to a
 * normalized official video. Those URLs are authoritative when supplied by
 * ExamPage. Cloudinary poster derivation is retained only as a compatibility
 * fallback for older API payloads. Demo/legacy symbolic media continue through
 * ExamMediaPremium unchanged, except for explicit aliases that repair obsolete
 * demo keys without weakening official media validation.
 */
export function MediaBlock({ mediaType, media, alt, poster, fallback }: ExamMediaRuntimeProps) {
  if (mediaType === 'video' && media && isPlayableUrl(media)) {
    const derivedPoster = /^https?:\/\//i.test(media) ? deriveCloudinaryPoster(media) : undefined;
    const effectivePoster = poster || derivedPoster;
    const effectiveFallback = fallback || effectivePoster;
    const playableMedia = normalizeCloudinaryVideoDelivery(media);

    if (effectivePoster || effectiveFallback) {
      return (
        <VideoPlayer
          url={playableMedia}
          poster={effectivePoster}
          fallbackUrl={effectiveFallback}
          alt={alt}
        />
      );
    }
  }

  const normalizedMedia = normalizeLegacySymbolicMedia(mediaType, media);
  return <PremiumMediaBlock mediaType={mediaType} media={normalizedMedia} alt={alt} />;
}

export { VideoPlayer };
