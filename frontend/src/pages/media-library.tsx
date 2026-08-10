import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useAuthSession } from '../authSession';
import {
  approveMediaQuality,
  approveMediaRegulatory,
  archiveMediaAsset,
  createMediaAsset,
  getMediaQualityGate,
  inspectMediaFile,
  listMediaAssets,
  rejectMediaQuality,
  rejectMediaRegulatory,
  sha256File,
  submitMediaQuality,
  submitMediaRegulatory,
  uploadMediaFile,
  type MediaAsset,
  type MediaQualityGate,
  type MediaSourceType,
  type MediaType,
  type MediaUsageType,
} from '../mediaApi';

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  review_required: 'Revue requise',
  validated: 'Validé',
  rejected: 'Rejeté',
  not_reviewed: 'Non revu',
  under_review: 'En revue',
};

function statusTone(value: string): string {
  if (value === 'validated') return 'var(--success, #15803d)';
  if (value === 'rejected') return 'var(--danger, #b91c1c)';
  if (value === 'review_required' || value === 'under_review') return 'var(--warning, #a16207)';
  return 'var(--muted)';
}

function MediaPreview({ asset }: { asset: MediaAsset }) {
  const url = asset.secure_url || asset.public_url;
  if (!url) return <div style={styles.emptyPreview}>Aucune URL de livraison</div>;
  if (asset.media_type === 'image') {
    return <img src={url} alt="Aperçu du média administrateur" loading="lazy" style={styles.preview} />;
  }
  if (asset.media_type === 'video') {
    return <video src={url} controls preload="metadata" playsInline style={styles.preview} />;
  }
  return <audio src={url} controls preload="metadata" style={{ width: '100%' }} />;
}

function Pill({ children, tone }: { children: React.ReactNode; tone?: string }) {
  return (
    <span style={{ ...styles.pill, color: tone ?? 'var(--text)', borderColor: tone ?? 'var(--border)' }}>
      {children}
    </span>
  );
}

export function MediaLibraryPage() {
  const { role } = useAuthSession();
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [qualityFilter, setQualityFilter] = useState('');
  const [regulatoryFilter, setRegulatoryFilter] = useState('');
  const [selected, setSelected] = useState<MediaAsset | null>(null);
  const [gate, setGate] = useState<MediaQualityGate | null>(null);
  const [reviewReason, setReviewReason] = useState('Contrôle média CodeRoute Guinée');
  const [authorityReference, setAuthorityReference] = useState('');

  const [file, setFile] = useState<File | null>(null);
  const [provider, setProvider] = useState('cloudinary');
  const [usageType, setUsageType] = useState<MediaUsageType>('exam');
  const [theme, setTheme] = useState('');
  const [sourceType, setSourceType] = useState<MediaSourceType>('original');
  const [sourceReference, setSourceReference] = useState('');
  const [licenseType, setLicenseType] = useState('');
  const [licenseReference, setLicenseReference] = useState('');
  const [copyrightOwner, setCopyrightOwner] = useState('');

  const isSuperAdmin = role === 'super_admin';

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await listMediaAssets({
        limit: 100,
        search,
        media_type: typeFilter,
        quality_status: qualityFilter,
        regulatory_status: regulatoryFilter,
      });
      setAssets(result.items);
      setTotal(result.total);
      if (selected) {
        const updated = result.items.find(item => item.id === selected.id);
        setSelected(updated ?? null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger la médiathèque');
    } finally {
      setLoading(false);
    }
  }, [qualityFilter, regulatoryFilter, search, selected?.id, typeFilter]);

  useEffect(() => { void refresh(); }, [qualityFilter, regulatoryFilter, typeFilter]);

  const counts = useMemo(() => ({
    validated: assets.filter(a => a.quality_status === 'validated' && a.regulatory_status === 'validated').length,
    review: assets.filter(a => a.quality_status === 'review_required' || a.regulatory_status === 'under_review').length,
    draft: assets.filter(a => a.quality_status === 'draft').length,
  }), [assets]);

  async function openAsset(asset: MediaAsset) {
    setSelected(asset);
    setGate(null);
    try { setGate(await getMediaQualityGate(asset.id)); } catch { setGate(null); }
  }

  async function runAction(action: () => Promise<MediaAsset>) {
    if (!selected) return;
    setBusy(true); setError('');
    try {
      const updated = await action();
      setSelected(updated);
      setGate(await getMediaQualityGate(updated.id).catch(() => null));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible');
    } finally { setBusy(false); }
  }

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) { setError('Sélectionnez un fichier média.'); return; }
    const mediaType: MediaType = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : file.type.startsWith('audio/') ? 'audio' : 'image';
    if (!file.type.startsWith(`${mediaType}/`)) { setError('Format de fichier non reconnu.'); return; }

    setBusy(true); setError('');
    try {
      const [checksum, metadata, upload] = await Promise.all([
        sha256File(file),
        inspectMediaFile(file, mediaType),
        uploadMediaFile(file, mediaType, provider),
      ]);
      const asset = await createMediaAsset({
        media_type: mediaType,
        usage_type: usageType,
        storage_provider: upload.provider,
        storage_key: upload.storageKey,
        secure_url: upload.secureUrl,
        mime_type: file.type,
        width: metadata.width,
        height: metadata.height,
        duration_seconds: metadata.duration_seconds,
        file_size_bytes: file.size,
        checksum_sha256: checksum,
        theme: theme || null,
        country_code: 'GN',
        regulatory_scope: usageType === 'exam' ? 'Guinée — examen code de la route' : 'Guinée — contenu pédagogique',
        source_type: sourceType,
        source_reference: sourceReference || null,
        license_type: licenseType || null,
        license_reference: licenseReference || null,
        copyright_owner: copyrightOwner || null,
      });
      setFile(null);
      setSelected(asset);
      setGate(await getMediaQualityGate(asset.id).catch(() => null));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload impossible');
    } finally { setBusy(false); }
  }

  return (
    <section className="screen" data-testid="media-library-page" style={{ maxWidth: 1440, margin: '0 auto', padding: 24 }}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Administration · Qualité média</p>
          <h1 style={{ margin: 0 }}>Médiathèque CodeRoute Guinée</h1>
          <p style={styles.muted}>Photos, vidéos et audios traçables. Une validation technique ne vaut jamais homologation DNTT.</p>
        </div>
        <div style={styles.metrics}>
          <div style={styles.metric}><strong>{total}</strong><span>Total</span></div>
          <div style={styles.metric}><strong>{counts.validated}</strong><span>Prêts</span></div>
          <div style={styles.metric}><strong>{counts.review}</strong><span>En revue</span></div>
          <div style={styles.metric}><strong>{counts.draft}</strong><span>Brouillons</span></div>
        </div>
      </header>

      {error && <div role="alert" style={styles.error}>{error}</div>}

      <div style={styles.layout}>
        <div style={{ display: 'grid', gap: 18 }}>
          <form onSubmit={handleUpload} style={styles.panel} data-testid="media-upload-form">
            <div style={styles.panelTitle}><strong>Ajouter un média</strong><span style={styles.muted}>Upload direct, SHA-256 calculé localement</span></div>
            <div style={styles.formGrid}>
              <label style={styles.label}>Fichier<input data-testid="media-file" type="file" accept="image/jpeg,image/png,image/webp,image/avif,video/mp4,video/webm,video/quicktime,audio/mpeg,audio/mp4,audio/ogg,audio/wav,audio/webm" onChange={e => setFile(e.target.files?.[0] ?? null)} /></label>
              <label style={styles.label}>Provider<select value={provider} onChange={e => setProvider(e.target.value)}><option value="cloudinary">Cloudinary</option><option value="s3">AWS S3</option><option value="r2">Cloudflare R2</option><option value="minio">MinIO</option></select></label>
              <label style={styles.label}>Usage<select value={usageType} onChange={e => setUsageType(e.target.value as MediaUsageType)}><option value="exam">Examen</option><option value="course">Cours</option><option value="explanation">Correction</option><option value="thumbnail">Thumbnail</option></select></label>
              <label style={styles.label}>Thème<input value={theme} onChange={e => setTheme(e.target.value)} placeholder="PRIORITES" /></label>
              <label style={styles.label}>Source<select value={sourceType} onChange={e => setSourceType(e.target.value as MediaSourceType)}><option value="original">Original</option><option value="licensed">Sous licence</option><option value="partner">Partenaire</option><option value="public_domain">Domaine public</option><option value="internal">Interne</option><option value="generated">Généré / 3D</option></select></label>
              <label style={styles.label}>Référence source<input value={sourceReference} onChange={e => setSourceReference(e.target.value)} placeholder="CAPTATION-2026-001" /></label>
              <label style={styles.label}>Type de licence<input value={licenseType} onChange={e => setLicenseType(e.target.value)} placeholder="commercial / original" /></label>
              <label style={styles.label}>Référence licence<input value={licenseReference} onChange={e => setLicenseReference(e.target.value)} placeholder="GED-LIC-0001" /></label>
              <label style={styles.label}>Copyright / propriétaire<input value={copyrightOwner} onChange={e => setCopyrightOwner(e.target.value)} /></label>
            </div>
            <button className="btn-primary" type="submit" disabled={busy || !file}>{busy ? 'Traitement…' : 'Uploader et enregistrer'}</button>
          </form>

          <div style={styles.panel}>
            <div style={styles.filters}>
              <input aria-label="Rechercher les médias" placeholder="Rechercher thème, source…" value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') void refresh(); }} />
              <select aria-label="Filtrer par type" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}><option value="">Tous types</option><option value="image">Images</option><option value="video">Vidéos</option><option value="audio">Audio</option></select>
              <select aria-label="Filtrer par qualité" value={qualityFilter} onChange={e => setQualityFilter(e.target.value)}><option value="">Toute qualité</option><option value="draft">Brouillon</option><option value="review_required">Revue requise</option><option value="validated">Validé</option><option value="rejected">Rejeté</option></select>
              <select aria-label="Filtrer par réglementation" value={regulatoryFilter} onChange={e => setRegulatoryFilter(e.target.value)}><option value="">Toute conformité</option><option value="not_reviewed">Non revue</option><option value="under_review">En revue</option><option value="validated">Validée</option><option value="rejected">Rejetée</option></select>
              <button className="btn-secondary" onClick={() => void refresh()} disabled={loading}>Actualiser</button>
            </div>

            {loading ? <p style={styles.muted}>Chargement…</p> : assets.length === 0 ? <p style={styles.muted}>Aucun média trouvé.</p> : (
              <div style={styles.grid} data-testid="media-grid">
                {assets.map(asset => (
                  <button key={asset.id} type="button" onClick={() => void openAsset(asset)} style={{ ...styles.card, ...(selected?.id === asset.id ? styles.cardSelected : {}) }} data-testid={`media-card-${asset.id}`}>
                    <div style={styles.cardPreview}><MediaPreview asset={asset} /></div>
                    <div style={{ display: 'grid', gap: 8, textAlign: 'left' }}>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}><Pill>{asset.media_type.toUpperCase()}</Pill><Pill>{asset.usage_type}</Pill></div>
                      <strong>{asset.theme || 'Sans thème'}</strong>
                      <span style={styles.muted}>{asset.width && asset.height ? `${asset.width}×${asset.height}` : 'Dimensions inconnues'}{asset.duration_seconds ? ` · ${asset.duration_seconds.toFixed(1)}s` : ''}</span>
                      <span style={{ color: statusTone(asset.quality_status) }}>Qualité : {STATUS_LABELS[asset.quality_status] ?? asset.quality_status}</span>
                      <span style={{ color: statusTone(asset.regulatory_status) }}>Réglementaire : {STATUS_LABELS[asset.regulatory_status] ?? asset.regulatory_status}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside style={styles.panel} data-testid="media-detail-panel">
          {!selected ? <p style={styles.muted}>Sélectionnez un média pour voir sa traçabilité et sa recette.</p> : (
            <div style={{ display: 'grid', gap: 16 }}>
              <MediaPreview asset={selected} />
              <div><strong>{selected.theme || 'Sans thème'}</strong><div style={styles.muted}>{selected.id}</div></div>
              <div style={styles.detailGrid}>
                <span>SHA-256</span><code style={styles.code}>{selected.checksum_sha256 || 'absent'}</code>
                <span>Source</span><strong>{selected.source_type}</strong>
                <span>Référence</span><span>{selected.source_reference || '—'}</span>
                <span>Licence</span><span>{selected.license_reference || selected.license_type || '—'}</span>
                <span>Autorité</span><span>{selected.regulatory_authority_reference || '—'}</span>
              </div>

              {gate && (
                <div style={styles.gate} data-testid="media-quality-gate">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><strong>Quality score</strong><strong>{gate.score}/100</strong></div>
                  <div style={{ height: 8, background: 'var(--border)', borderRadius: 999, overflow: 'hidden' }}><div style={{ width: `${gate.score}%`, height: '100%', background: gate.passed ? 'var(--success, #15803d)' : 'var(--warning, #a16207)' }} /></div>
                  {gate.blockers.length > 0 && <ul style={{ margin: 0, paddingLeft: 18 }}>{gate.blockers.map(blocker => <li key={blocker} style={{ fontSize: 12 }}>{blocker}</li>)}</ul>}
                </div>
              )}

              <label style={styles.label}>Motif de revue<textarea rows={3} value={reviewReason} onChange={e => setReviewReason(e.target.value)} /></label>
              {isSuperAdmin && <label style={styles.label}>Référence autorité<input data-testid="authority-reference" value={authorityReference} onChange={e => setAuthorityReference(e.target.value)} placeholder="DNTT-MEDIA-2026-…" /></label>}

              <div style={styles.actions}>
                {selected.quality_status !== 'validated' && <button className="btn-secondary" disabled={busy} onClick={() => void runAction(() => submitMediaQuality(selected.id, reviewReason))}>Soumettre qualité</button>}
                {selected.quality_status === 'review_required' && <button className="btn-primary" disabled={busy} onClick={() => void runAction(() => approveMediaQuality(selected.id, reviewReason))}>Valider qualité</button>}
                {selected.quality_status === 'review_required' && <button className="btn-secondary" disabled={busy} onClick={() => void runAction(() => rejectMediaQuality(selected.id, reviewReason))}>Rejeter qualité</button>}
                {selected.quality_status === 'validated' && selected.regulatory_status !== 'validated' && <button className="btn-secondary" disabled={busy} onClick={() => void runAction(() => submitMediaRegulatory(selected.id, reviewReason))}>Soumettre réglementaire</button>}
                {isSuperAdmin && selected.regulatory_status === 'under_review' && <button className="btn-primary" data-testid="approve-regulatory" disabled={busy || authorityReference.trim().length < 3} onClick={() => void runAction(() => approveMediaRegulatory(selected.id, authorityReference, reviewReason))}>Valider réglementaire</button>}
                {isSuperAdmin && selected.regulatory_status === 'under_review' && <button className="btn-secondary" disabled={busy} onClick={() => void runAction(() => rejectMediaRegulatory(selected.id, reviewReason))}>Rejeter réglementaire</button>}
                <button className="btn-secondary" disabled={busy} onClick={() => void runAction(() => archiveMediaAsset(selected.id))}>Archiver</button>
              </div>
              <p style={styles.notice}>La plateforme ne déclare jamais une homologation institutionnelle automatiquement. La référence d’autorité doit correspondre à une décision réelle et vérifiable.</p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap', marginBottom: 20 },
  eyebrow: { margin: 0, textTransform: 'uppercase', letterSpacing: '.08em', fontSize: 11, fontWeight: 700, color: 'var(--muted)' },
  muted: { color: 'var(--muted)', fontSize: 13, margin: 0 },
  metrics: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  metric: { minWidth: 88, border: '1px solid var(--border)', background: 'var(--surface)', padding: '10px 12px', borderRadius: 12, display: 'grid', gap: 2 },
  layout: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(300px, 380px)', gap: 18, alignItems: 'start' },
  panel: { border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 16, padding: 16, boxShadow: '0 8px 24px rgba(0,0,0,.04)' },
  panelTitle: { display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 14 },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12, marginBottom: 14 },
  label: { display: 'grid', gap: 6, fontSize: 12, fontWeight: 600 },
  filters: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 12 },
  card: { border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 12, padding: 10, cursor: 'pointer', color: 'inherit' },
  cardSelected: { outline: '2px solid var(--primary)', outlineOffset: 1 },
  cardPreview: { aspectRatio: '16/9', borderRadius: 9, overflow: 'hidden', background: 'var(--bg)', marginBottom: 10, display: 'grid', placeItems: 'center' },
  preview: { width: '100%', height: '100%', maxHeight: 280, objectFit: 'cover', display: 'block' },
  emptyPreview: { minHeight: 120, display: 'grid', placeItems: 'center', color: 'var(--muted)', fontSize: 12 },
  pill: { border: '1px solid var(--border)', borderRadius: 999, padding: '2px 7px', fontSize: 10, fontWeight: 700 },
  detailGrid: { display: 'grid', gridTemplateColumns: '88px minmax(0,1fr)', gap: '8px 10px', fontSize: 12 },
  code: { overflowWrap: 'anywhere', fontSize: 10 },
  gate: { display: 'grid', gap: 10, padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg)' },
  actions: { display: 'flex', flexWrap: 'wrap', gap: 8 },
  notice: { margin: 0, padding: 10, borderRadius: 10, background: 'var(--bg)', color: 'var(--muted)', fontSize: 11, lineHeight: 1.5 },
  error: { marginBottom: 16, padding: 12, borderRadius: 10, border: '1px solid var(--danger, #b91c1c)', color: 'var(--danger, #b91c1c)' },
};
