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

function isPlayableUrl(url: string): boolean {
  return /^https?:\/\//i.test(url) || url.startsWith('/media/');
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
 * normalized official video. Those URLs are now authoritative when supplied
 * by ExamPage. Cloudinary poster derivation is retained only as a compatibility
 * fallback for older API payloads. Demo/legacy symbolic media continue through
 * ExamMediaPremium unchanged.
 */
export function MediaBlock({ mediaType, media, alt, poster, fallback }: ExamMediaRuntimeProps) {
  if (mediaType === 'video' && media && isPlayableUrl(media)) {
    const derivedPoster = /^https?:\/\//i.test(media) ? deriveCloudinaryPoster(media) : undefined;
    const effectivePoster = poster || derivedPoster;
    const effectiveFallback = fallback || effectivePoster;

    if (effectivePoster || effectiveFallback) {
      return (
        <VideoPlayer
          url={media}
          poster={effectivePoster}
          fallbackUrl={effectiveFallback}
          alt={alt}
        />
      );
    }
  }

  return <PremiumMediaBlock mediaType={mediaType} media={media} alt={alt} />;
}

export { VideoPlayer };
