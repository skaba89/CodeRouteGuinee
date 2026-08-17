import { useRef, useState } from 'react';
import { MediaBlock as LegacyMediaBlock, SignSvg } from '../pages/shared-exam-components-legacy';

const OFFICIAL_ATTEMPT_KEY = 'coderoute:official-exam:active-attempt';
const GUINEA_MEDIA_BASE = '/media/exam/guinea';
const GUINEA_MEDIA_VERSION = '20260817-1';

type DemoMediaOverride = {
  mediaType: 'image' | 'video';
  url: string;
  poster?: string;
  fallback?: string;
  fallbackSign?: string;
};

function demoAsset(filename: string): string {
  return `${GUINEA_MEDIA_BASE}/${filename}?v=${GUINEA_MEDIA_VERSION}`;
}

function withRetryCacheBypass(url: string, retryKey: number): string {
  if (retryKey <= 0) return url;
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}retry=${retryKey}`;
}

function normalizeLabel(value?: string): string {
  return (value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function isOfficialAttemptActive(): boolean {
  try {
    return Boolean(window.sessionStorage.getItem(OFFICIAL_ATTEMPT_KEY));
  } catch {
    // Fail closed: if browser storage cannot be inspected, do not inject demo assets.
    return true;
  }
}

function resolveGuineaDemoMedia(media?: string, alt?: string): DemoMediaOverride | null {
  if (!media || isOfficialAttemptActive()) return null;
  const key = media.trim().toLowerCase();
  const label = normalizeLabel(alt);

  if (key === 'stop' && label.includes('stop')) {
    return { mediaType: 'image', url: demoAsset('stop-conakry.webp'), fallbackSign: 'stop' };
  }
  if (key === 'give_way' && (label.includes('cedez') || label.includes('passage'))) {
    return { mediaType: 'image', url: demoAsset('yield-roundabout-conakry.webp'), fallbackSign: 'give_way' };
  }
  if (key === 'no_entry' && (label.includes('sens interdit') || label.includes('interdit'))) {
    return { mediaType: 'image', url: demoAsset('no-entry-conakry.webp'), fallbackSign: 'no_entry' };
  }
  if (key === 'roundabout' && (label.includes('giratoire') || label.includes('rond-point') || label.includes('rond point'))) {
    return {
      mediaType: 'video',
      url: demoAsset('roundabout-approach-demo.mp4'),
      poster: demoAsset('yield-roundabout-conakry.webp'),
      fallback: demoAsset('yield-roundabout-conakry.webp'),
    };
  }
  return null;
}

function isRenderableMediaUrl(url: string): boolean {
  return /^https?:\/\//i.test(url) || url.startsWith('/media/');
}

function deriveCloudinaryPoster(url: string): string | undefined {
  try {
    const parsed = new URL(url);
    if (parsed.hostname !== 'res.cloudinary.com' || !parsed.pathname.includes('/video/upload/')) return undefined;
    const nextPath = parsed.pathname.replace(/\.[a-z0-9]+$/i, '.jpg');
    return `${parsed.origin}${nextPath}`;
  } catch {
    return undefined;
  }
}

function hasVisiblePixelVariation(image: HTMLImageElement): boolean {
  try {
    const resolved = new URL(image.currentSrc || image.src, window.location.href);
    if (resolved.origin !== window.location.origin || !resolved.pathname.startsWith(`${GUINEA_MEDIA_BASE}/`)) {
      return true;
    }

    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 18;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return true;

    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let opaquePixels = 0;
    let minLuma = 255;
    let maxLuma = 0;
    let chromaticPixels = 0;

    for (let index = 0; index < pixels.length; index += 4) {
      const red = pixels[index];
      const green = pixels[index + 1];
      const blue = pixels[index + 2];
      const alpha = pixels[index + 3];
      if (alpha < 32) continue;

      opaquePixels += 1;
      const luma = Math.round(0.2126 * red + 0.7152 * green + 0.0722 * blue);
      minLuma = Math.min(minLuma, luma);
      maxLuma = Math.max(maxLuma, luma);
      if (Math.max(red, green, blue) - Math.min(red, green, blue) >= 16) {
        chromaticPixels += 1;
      }
    }

    const sampleCount = canvas.width * canvas.height;
    const enoughOpaqueContent = opaquePixels >= sampleCount * 0.8;
    const enoughContrast = maxLuma - minLuma >= 18;
    const enoughSignal = maxLuma >= 48 || chromaticPixels >= 8;
    return enoughOpaqueContent && enoughContrast && enoughSignal;
  } catch {
    // A canvas security/decoding error must not reject unrelated remote media.
    return true;
  }
}

async function requestFullscreen(element: HTMLElement | null): Promise<void> {
  if (!element || !document.fullscreenEnabled) return;
  try {
    await element.requestFullscreen();
  } catch {
    // Le bouton natif du navigateur reste disponible dans les contrôles vidéo.
  }
}

function MediaCaption({ alt }: { alt?: string }) {
  if (!alt) return null;
  return (
    <div style={{ padding: '8px 12px', background: '#0d2137', color: 'rgba(255,255,255,.9)', fontSize: 11.5, lineHeight: 1.5, textAlign: 'center' }}>
      {alt}
    </div>
  );
}

export function VideoPlayer({ url, poster, fallbackUrl, alt }: { url: string; poster?: string; fallbackUrl?: string; alt?: string }) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [retryKey, setRetryKey] = useState(0);
  const effectivePoster = poster ?? deriveCloudinaryPoster(url);

  function retry() {
    setState('loading');
    setRetryKey(key => key + 1);
  }

  return (
    <div ref={frameRef} data-testid="exam-media-video-frame" style={{ borderRadius: 14, overflow: 'hidden', background: '#000', position: 'relative', boxShadow: '0 10px 30px rgba(13,33,55,.22)' }}>
      <div style={{ aspectRatio: '16 / 9', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#07111c,#0d2137)' }}>
        {state === 'loading' && (
          <div aria-live="polite" style={{ position: 'absolute', inset: 0, zIndex: 1, display: 'grid', placeItems: 'center', color: 'rgba(255,255,255,.78)', fontSize: 12 }}>
            <div style={{ padding: '8px 12px', borderRadius: 20, background: 'rgba(0,0,0,.38)', backdropFilter: 'blur(4px)' }}>Chargement de la vidéo…</div>
          </div>
        )}

        {state !== 'error' ? (
          <video
            key={retryKey}
            ref={videoRef}
            data-testid="exam-media-video"
            src={url}
            poster={effectivePoster}
            controls
            controlsList="nodownload"
            preload="metadata"
            playsInline
            onLoadedData={() => setState('ready')}
            onCanPlay={() => setState('ready')}
            onError={() => setState('error')}
            aria-label={alt ?? 'Vidéo de situation routière'}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', background: '#000' }}
          >
            <p>Votre navigateur ne supporte pas la lecture vidéo HTML5.</p>
          </video>
        ) : fallbackUrl ? (
          <div role="alert" style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', background: '#000' }}>
            <img data-testid="exam-media-video-fallback" src={fallbackUrl} alt={alt ?? 'Image de secours de la situation routière'} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            <div style={{ position: 'absolute', left: 10, right: 10, bottom: 10, display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', color: '#fff', padding: '7px 10px', borderRadius: 9, background: 'rgba(0,0,0,.68)', fontSize: 11.5 }}>
              <span>Vidéo indisponible — image de secours affichée.</span>
              <button type="button" className="secondary-button btn-sm" onClick={retry}>Réessayer</button>
            </div>
          </div>
        ) : (
          <div role="alert" style={{ color: '#fff', textAlign: 'center', padding: 20, maxWidth: 360 }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Vidéo momentanément indisponible</div>
            <div style={{ color: 'rgba(255,255,255,.68)', fontSize: 12, lineHeight: 1.5, marginBottom: 12 }}>
              Vérifiez la connexion puis relancez le chargement. La question reste utilisable.
            </div>
            <button type="button" className="secondary-button btn-sm" onClick={retry}>Réessayer</button>
          </div>
        )}

        {state === 'ready' && document.fullscreenEnabled && (
          <button
            type="button"
            onClick={() => { void requestFullscreen(frameRef.current); }}
            aria-label="Afficher la vidéo en plein écran"
            style={{ position: 'absolute', top: 10, right: 10, zIndex: 2, border: '1px solid rgba(255,255,255,.35)', borderRadius: 8, background: 'rgba(0,0,0,.55)', color: '#fff', padding: '6px 9px', fontSize: 11, cursor: 'pointer', minHeight: 'unset' }}
          >
            Plein écran
          </button>
        )}
      </div>
      <MediaCaption alt={alt} />
    </div>
  );
}

function PremiumImage({ url, alt, fallbackSign }: { url: string; alt?: string; fallbackSign?: string }) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [retryKey, setRetryKey] = useState(0);
  const imageUrl = withRetryCacheBypass(url, retryKey);

  function retry() {
    setState('loading');
    setRetryKey(key => key + 1);
  }

  return (
    <div ref={frameRef} data-testid="exam-media-image-frame" style={{ borderRadius: 14, overflow: 'hidden', background: '#0d2137', border: '1px solid var(--border)', boxShadow: '0 8px 24px rgba(13,33,55,.12)' }}>
      <div data-testid="exam-media-image-viewport" style={{ aspectRatio: '16 / 9', position: 'relative', overflow: 'hidden', background: '#0d2137' }}>
        {state === 'loading' && (
          <div aria-live="polite" style={{ position: 'absolute', inset: 0, zIndex: 1, display: 'grid', placeItems: 'center', color: 'rgba(255,255,255,.78)', fontSize: 12, background: 'linear-gradient(135deg,#0d2137,#1b3254)' }}>
            Chargement de l'image…
          </div>
        )}

        {state !== 'error' ? (
          <img
            key={imageUrl}
            data-testid="exam-media-image"
            src={imageUrl}
            alt={alt ?? 'Illustration de la question'}
            loading="eager"
            decoding="async"
            onLoad={(event) => {
              const image = event.currentTarget;
              const { naturalWidth, naturalHeight } = image;
              if (naturalWidth < 320 || naturalHeight < 180 || !hasVisiblePixelVariation(image)) {
                setState('error');
                return;
              }
              setState('ready');
            }}
            onError={() => setState('error')}
            style={{
              position: 'absolute',
              inset: 0,
              zIndex: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: 'center',
              display: 'block',
              opacity: state === 'ready' ? 1 : 0,
              visibility: state === 'ready' ? 'visible' : 'hidden',
              transition: 'opacity 160ms ease-out',
            }}
          />
        ) : fallbackSign ? (
          <div role="alert" data-testid="exam-media-image-fallback" style={{ position: 'absolute', inset: 0, zIndex: 1, display: 'grid', placeItems: 'center', textAlign: 'center', padding: 20, color: '#fff', background: 'linear-gradient(135deg,#0d2137,#1b3254)' }}>
            <div style={{ maxWidth: 360 }}>
              <SignSvg type={fallbackSign} alt={alt} />
              <div style={{ fontWeight: 800, marginTop: 10, marginBottom: 6 }}>Image indisponible — panneau de secours affiché</div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,.72)', lineHeight: 1.5, marginBottom: 12 }}>
                Le média photo n'a pas pu être rendu correctement. Le panneau correspondant reste visible pour ne pas rendre la question ambiguë.
              </div>
              <button type="button" className="secondary-button btn-sm" onClick={retry}>Réessayer</button>
            </div>
          </div>
        ) : (
          <div role="alert" style={{ position: 'absolute', inset: 0, zIndex: 1, display: 'grid', placeItems: 'center', textAlign: 'center', padding: 20, color: '#fff', background: 'linear-gradient(135deg,#0d2137,#1b3254)' }}>
            <div style={{ maxWidth: 360 }}>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Image momentanément indisponible</div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,.72)', lineHeight: 1.5, marginBottom: 12 }}>
                Le média n'a pas pu être rendu correctement. Vous pouvez continuer l'épreuve ou tenter un nouveau chargement.
              </div>
              <button type="button" className="secondary-button btn-sm" onClick={retry}>Réessayer</button>
            </div>
          </div>
        )}

        {state === 'ready' && document.fullscreenEnabled && (
          <button
            type="button"
            onClick={() => { void requestFullscreen(frameRef.current); }}
            aria-label="Afficher l'image en plein écran"
            style={{ position: 'absolute', top: 10, right: 10, zIndex: 2, border: '1px solid rgba(255,255,255,.45)', borderRadius: 8, background: 'rgba(0,0,0,.62)', color: '#fff', padding: '6px 9px', fontSize: 11, cursor: 'pointer', minHeight: 'unset', boxShadow: '0 2px 8px rgba(13,33,55,.18)' }}
          >
            Plein écran
          </button>
        )}
      </div>
      <MediaCaption alt={alt} />
    </div>
  );
}

export function MediaBlock({ mediaType, media, alt }: { mediaType?: string; media?: string; alt?: string }) {
  if (!media) return null;

  const demo = resolveGuineaDemoMedia(media, alt);
  if (demo?.mediaType === 'video') {
    return <VideoPlayer url={demo.url} poster={demo.poster} fallbackUrl={demo.fallback} alt={alt} />;
  }
  if (demo?.mediaType === 'image') {
    return <PremiumImage url={demo.url} alt={alt} fallbackSign={demo.fallbackSign} />;
  }

  if (mediaType === 'video' && isRenderableMediaUrl(media)) {
    return <VideoPlayer url={media} alt={alt} />;
  }
  if (mediaType === 'image' && isRenderableMediaUrl(media)) {
    return <PremiumImage url={media} alt={alt} />;
  }
  return <LegacyMediaBlock mediaType={mediaType} media={media} alt={alt} />;
}
