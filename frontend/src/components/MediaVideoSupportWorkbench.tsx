import { useState, type CSSProperties } from 'react';
import { listMediaAssets, type MediaAsset } from '../mediaApi';
import { configureVideoSupportMedia } from '../mediaVideoApi';

function assetLabel(asset: MediaAsset): string {
  const theme = asset.theme || 'Sans thème';
  const size = asset.width && asset.height ? `${asset.width}×${asset.height}` : 'dimensions inconnues';
  return `${theme} · ${size} · ${asset.id}`;
}

export function MediaVideoSupportWorkbench() {
  const [videos, setVideos] = useState<MediaAsset[]>([]);
  const [images, setImages] = useState<MediaAsset[]>([]);
  const [videoSearch, setVideoSearch] = useState('');
  const [imageSearch, setImageSearch] = useState('');
  const [selectedVideo, setSelectedVideo] = useState<MediaAsset | null>(null);
  const [posterId, setPosterId] = useState('');
  const [fallbackId, setFallbackId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function searchVideos() {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await listMediaAssets({
        limit: 50,
        media_type: 'video',
        usage_type: 'exam',
        search: videoSearch || undefined,
      });
      setVideos(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recherche de vidéos impossible');
    } finally { setBusy(false); }
  }

  async function searchImages() {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await listMediaAssets({
        limit: 100,
        media_type: 'image',
        quality_status: 'validated',
        search: imageSearch || undefined,
      });
      setImages(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recherche d’images impossible');
    } finally { setBusy(false); }
  }

  function chooseVideo(video: MediaAsset) {
    setSelectedVideo(video);
    setPosterId(video.poster_media_id || '');
    setFallbackId(video.fallback_media_id || '');
    setError(''); setNotice('');
  }

  async function save() {
    if (!selectedVideo || !posterId || !fallbackId) return;
    if (posterId === selectedVideo.id || fallbackId === selectedVideo.id) {
      setError('Une vidéo ne peut pas utiliser son propre MediaAsset comme poster ou fallback.');
      return;
    }

    setBusy(true); setError(''); setNotice('');
    try {
      const updated = await configureVideoSupportMedia(selectedVideo.id, posterId, fallbackId);
      setSelectedVideo(updated);
      setVideos(current => current.map(item => item.id === updated.id ? updated : item));
      setNotice('Poster et fallback enregistrés. Le backend invalide les validations sensibles : relancez ensuite la revue qualité puis réglementaire.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Configuration impossible');
    } finally { setBusy(false); }
  }

  return (
    <section data-testid="media-video-support-workbench" style={s.shell}>
      <header style={s.header}>
        <div>
          <p style={s.eyebrow}>Vidéo officielle · résilience</p>
          <h2 style={{ margin: 0 }}>Configurer poster et image de secours</h2>
          <p style={s.muted}>Une vidéo d’examen ne peut passer le quality gate sans deux images validées : poster + fallback.</p>
        </div>
        <span style={s.badge}>MediaAsset.video</span>
      </header>

      {error && <div role="alert" style={s.error}>{error}</div>}
      {notice && <div role="status" style={s.success}>{notice}</div>}

      <div style={s.columns}>
        <div style={s.panel}>
          <strong>1. Vidéo d’examen</strong>
          <div style={s.searchRow}>
            <input value={videoSearch} onChange={e => setVideoSearch(e.target.value)} placeholder="Thème ou source…" aria-label="Rechercher une vidéo d’examen" />
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => void searchVideos()}>Rechercher</button>
          </div>
          <div style={s.list}>
            {videos.map(video => (
              <button
                key={video.id}
                type="button"
                onClick={() => chooseVideo(video)}
                style={{ ...s.item, ...(selectedVideo?.id === video.id ? s.selected : {}) }}
                data-testid={`video-support-${video.id}`}
              >
                <strong>{video.theme || 'Sans thème'}</strong>
                <span style={s.muted}>{video.duration_seconds ? `${video.duration_seconds.toFixed(1)} s` : 'Durée inconnue'} · {video.quality_status} / {video.regulatory_status}</span>
                <code style={s.code}>{video.id}</code>
              </button>
            ))}
            {videos.length === 0 && <span style={s.muted}>Recherchez une vidéo `usage_type=exam`.</span>}
          </div>
        </div>

        <div style={s.panel}>
          <strong>2. Images de support validées</strong>
          <div style={s.searchRow}>
            <input value={imageSearch} onChange={e => setImageSearch(e.target.value)} placeholder="Thème ou source…" aria-label="Rechercher des images support" />
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => void searchImages()}>Rechercher</button>
          </div>

          <label style={s.label}>Poster
            <select value={posterId} onChange={e => setPosterId(e.target.value)} disabled={!selectedVideo} data-testid="video-poster-select">
              <option value="">Choisir une image validée</option>
              {images.map(image => <option key={`poster-${image.id}`} value={image.id}>{assetLabel(image)}</option>)}
            </select>
          </label>

          <label style={s.label}>Fallback si la vidéo ne charge pas
            <select value={fallbackId} onChange={e => setFallbackId(e.target.value)} disabled={!selectedVideo} data-testid="video-fallback-select">
              <option value="">Choisir une image validée</option>
              {images.map(image => <option key={`fallback-${image.id}`} value={image.id}>{assetLabel(image)}</option>)}
            </select>
          </label>

          <button type="button" className="btn-primary" disabled={busy || !selectedVideo || !posterId || !fallbackId} onClick={() => void save()} data-testid="save-video-support">
            Enregistrer poster + fallback
          </button>
        </div>
      </div>

      {selectedVideo && (
        <div style={s.notice}>
          <strong>Workflow obligatoire après modification</strong>
          <span>PATCH MediaAsset → validations sensibles invalidées → revue qualité à quatre yeux → revue réglementaire → association `primary` à la question.</span>
          <span>Le poster/fallback n’accorde jamais une homologation DNTT automatiquement.</span>
        </div>
      )}
    </section>
  );
}

const s: Record<string, CSSProperties> = {
  shell: { maxWidth: 1440, margin: '18px auto 40px', padding: 24, display: 'grid', gap: 16 },
  header: { display: 'flex', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap' },
  eyebrow: { margin: 0, textTransform: 'uppercase', letterSpacing: '.08em', fontSize: 11, fontWeight: 800, color: 'var(--muted)' },
  muted: { margin: 0, color: 'var(--muted)', fontSize: 12, lineHeight: 1.5 },
  badge: { padding: '5px 9px', border: '1px solid var(--border)', borderRadius: 999, fontSize: 11, fontWeight: 700 },
  columns: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 14 },
  panel: { padding: 16, border: '1px solid var(--border)', borderRadius: 16, background: 'var(--surface)', display: 'grid', gap: 12, boxShadow: '0 8px 24px rgba(0,0,0,.04)' },
  searchRow: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  list: { display: 'grid', gap: 8, maxHeight: 320, overflow: 'auto' },
  item: { display: 'grid', gap: 4, textAlign: 'left', padding: 10, border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)', color: 'inherit', cursor: 'pointer' },
  selected: { outline: '2px solid var(--primary)', outlineOffset: 1 },
  label: { display: 'grid', gap: 6, fontSize: 12, fontWeight: 700 },
  code: { fontSize: 9, color: 'var(--muted)', overflowWrap: 'anywhere' },
  notice: { display: 'grid', gap: 6, padding: 14, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg)', fontSize: 12, lineHeight: 1.5 },
  error: { padding: 12, borderRadius: 10, border: '1px solid var(--danger,#b91c1c)', color: 'var(--danger,#b91c1c)' },
  success: { padding: 12, borderRadius: 10, border: '1px solid var(--success,#15803d)', color: 'var(--success,#15803d)' },
};
