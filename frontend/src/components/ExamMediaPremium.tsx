import { useRef, useState } from 'react';
import { MediaBlock as LegacyMediaBlock } from '../pages/shared-exam-components-legacy';

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

export function VideoPlayer({ url, poster, alt }: { url: string; poster?: string; alt?: string }) {
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
    <div ref={frameRef} style={{ borderRadius: 14, overflow: 'hidden', background: '#000', position: 'relative', boxShadow: '0 10px 30px rgba(13,33,55,.22)' }}>
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

function PremiumImage({ url, alt }: { url: string; alt?: string }) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [retryKey, setRetryKey] = useState(0);

  return (
    <div ref={frameRef} style={{ borderRadius: 14, overflow: 'hidden', background: '#f5f7fa', border: '1px solid var(--border)', boxShadow: '0 8px 24px rgba(13,33,55,.12)' }}>
      <div style={{ aspectRatio: '16 / 9', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#edf2f7,#f8fafc)' }}>
        {state === 'loading' && (
          <div aria-live="polite" style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--muted)', fontSize: 12 }}>
            Chargement de l'image…
          </div>
        )}

        {state !== 'error' ? (
          <img
            key={retryKey}
            src={url}
            alt={alt ?? 'Illustration de la question'}
            loading="eager"
            decoding="async"
            onLoad={() => setState('ready')}
            onError={() => setState('error')}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: state === 'loading' ? 'none' : 'block' }}
          />
        ) : (
          <div role="alert" style={{ textAlign: 'center', padding: 20, color: 'var(--ink2)', maxWidth: 360 }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Image momentanément indisponible</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5, marginBottom: 12 }}>
              La connexion peut être instable. Vous pouvez continuer l'épreuve ou tenter un nouveau chargement.
            </div>
            <button type="button" className="secondary-button btn-sm" onClick={() => { setState('loading'); setRetryKey(key => key + 1); }}>Réessayer</button>
          </div>
        )}

        {state === 'ready' && document.fullscreenEnabled && (
          <button
            type="button"
            onClick={() => { void requestFullscreen(frameRef.current); }}
            aria-label="Afficher l'image en plein écran"
            style={{ position: 'absolute', top: 10, right: 10, border: '1px solid rgba(13,33,55,.18)', borderRadius: 8, background: 'rgba(255,255,255,.9)', color: '#0d2137', padding: '6px 9px', fontSize: 11, cursor: 'pointer', minHeight: 'unset', boxShadow: '0 2px 8px rgba(13,33,55,.12)' }}
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
  if (mediaType === 'video' && /^https?:\/\//i.test(media)) {
    return <VideoPlayer url={media} alt={alt} />;
  }
  if (mediaType === 'image' && /^https?:\/\//i.test(media)) {
    return <PremiumImage url={media} alt={alt} />;
  }
  return <LegacyMediaBlock mediaType={mediaType} media={media} alt={alt} />;
}
