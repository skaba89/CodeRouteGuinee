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
 * Runtime media facade used by exam screens.
 *
 * Cloudinary is the configured production media provider today. When an
 * official video URL comes from Cloudinary, its derived poster is also used as
 * a last-resort image fallback. Demo/legacy media continue through the existing
 * premium resolver unchanged.
 */
export function MediaBlock({ mediaType, media, alt }: { mediaType?: string; media?: string; alt?: string }) {
  if (mediaType === 'video' && media && /^https?:\/\//i.test(media)) {
    const poster = deriveCloudinaryPoster(media);
    if (poster) {
      return <VideoPlayer url={media} poster={poster} fallbackUrl={poster} alt={alt} />;
    }
  }
  return <PremiumMediaBlock mediaType={mediaType} media={media} alt={alt} />;
}

export { VideoPlayer };
