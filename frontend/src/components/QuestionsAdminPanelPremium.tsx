import { useEffect, useState } from 'react';
import {
  type ExamQuestion,
  getPrivateJson,
  getQuestions,
  importWikimediaSigns,
  signMediaUpload,
  updateQuestionMedia,
  uploadToCloudinary,
} from '../api';
import {
  FALLBACK_MEDIA_POLICIES,
  detectMediaKind,
  formatBytes,
  inspectMediaFile,
  type MediaInspection,
  type MediaKind,
  type MediaUploadPolicy,
} from './mediaUploadPolicy';

type MediaCoverage = {
  questions_total: number;
  with_media: number;
  without_media: number;
  coverage_percent: number;
  images: number;
  videos: number;
  missing_alt: number;
  insecure_legacy_urls: number;
  approved_questions: number;
  approved_with_media: number;
  approved_media_percent: number;
};

type SignatureWithPolicy = Awaited<ReturnType<typeof signMediaUpload>> & {
  policy?: MediaUploadPolicy;
};

function humanDuration(seconds?: number): string {
  if (seconds === undefined) return '—';
  return `${seconds.toFixed(seconds >= 10 ? 0 : 1)} s`;
}

function urlAllowed(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return true;
  return /^https:\/\//i.test(trimmed) || /^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?\//i.test(trimmed);
}

function CoverageCard({ coverage }: { coverage: MediaCoverage }) {
  const items = [
    ['Couverture active', `${coverage.coverage_percent}%`],
    ['Images', String(coverage.images)],
    ['Vidéos', String(coverage.videos)],
    ['ALT manquants', String(coverage.missing_alt)],
    ['URLs legacy HTTP', String(coverage.insecure_legacy_urls)],
    ['Couverture approuvée', `${coverage.approved_media_percent}%`],
  ];
  return (
    <div className="card" style={{ padding: 14 }}>
      <div className="card-header" style={{ marginBottom: 10 }}>
        <span className="card-title">Media Factory — couverture</span>
        <span className="badge bb">{coverage.with_media}/{coverage.questions_total}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 8 }}>
        {items.map(([label, value]) => (
          <div key={label} style={{ padding: '9px 10px', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg)' }}>
            <div style={{ fontSize: 10.5, color: 'var(--muted)', marginBottom: 3 }}>{label}</div>
            <strong style={{ fontSize: 16 }}>{value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function WikimediaImportButton({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const result = await importWikimediaSigns(true);
      if (result.signs_available === 0) {
        setMsg("Aucun panneau n'a pu être vérifié. Réessayez plus tard.");
      } else {
        setMsg(`${result.questions_updated} question(s) mises à jour · ${result.signs_available} panneaux vérifiés.`);
        onDone();
      }
    } catch (error) {
      setMsg(error instanceof Error ? error.message : 'Import impossible.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
      <button className="btn-sm btn-outline" onClick={run} disabled={busy}>
        {busy ? 'Import en cours…' : 'Importer les panneaux officiels'}
      </button>
      {msg && <span style={{ fontSize: 11, color: 'var(--muted)', maxWidth: 360, textAlign: 'right' }}>{msg}</span>}
    </div>
  );
}

export function QuestionsAdminPanel({ canAdmin }: { canAdmin: boolean }) {
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [coverage, setCoverage] = useState<MediaCoverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [editing, setEditing] = useState<ExamQuestion | null>(null);

  const reload = () => {
    setLoading(true);
    Promise.allSettled([
      getQuestions({ limit: 200 }),
      getPrivateJson<MediaCoverage>('/api/v1/questions/media-coverage'),
    ]).then(([questionResult, coverageResult]) => {
      if (questionResult.status === 'fulfilled') setQuestions(questionResult.value.items);
      if (coverageResult.status === 'fulfilled') setCoverage(coverageResult.value);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!canAdmin) {
      setLoading(false);
      return;
    }
    reload();
  }, [canAdmin]);

  if (!canAdmin) return <div className="alert aw">Accès réservé aux administrateurs.</div>;

  const filtered = filter
    ? questions.filter(question =>
        question.category.toLowerCase().includes(filter.toLowerCase())
        || question.text.toLowerCase().includes(filter.toLowerCase()))
    : questions;
  const byCategory = filtered.reduce<Record<string, number>>((acc, question) => {
    acc[question.category] = (acc[question.category] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {coverage && <CoverageCard coverage={coverage} />}

      <div className="card">
        <div className="card-header">
          <span className="card-title">Banque de questions ({questions.length})</span>
          <WikimediaImportButton onDone={reload} />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {Object.entries(byCategory).map(([category, count]) => (
            <button
              key={category}
              type="button"
              className={filter === category ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
              onClick={() => setFilter(filter === category ? '' : category)}
            >
              {category} ({count})
            </button>
          ))}
          {filter && <button className="btn-sm btn-danger" onClick={() => setFilter('')}>Effacer</button>}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{filter ? `${filter} — ` : ''}{filtered.length} question(s)</span>
          <button className="secondary-button btn-sm" onClick={reload} disabled={loading}>Actualiser</button>
        </div>
        {loading ? (
          <p className="text-muted" style={{ padding: 12 }}>Chargement…</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Catégorie</th><th>Question</th><th>Active</th><th>Média</th></tr></thead>
              <tbody>
                {filtered.slice(0, 200).map(question => (
                  <tr key={question.id}>
                    <td><span className="badge bb" style={{ fontSize: 10 }}>{question.category}</span></td>
                    <td style={{ fontSize: 12, maxWidth: 440, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{question.text}</td>
                    <td><span className={`badge ${question.is_active ? 'bg' : 'bgr'}`}>{question.is_active ? 'Oui' : 'Non'}</span></td>
                    <td>
                      {question.media_type === 'image' || question.media_type === 'video'
                        ? <span className="badge bg" style={{ fontSize: 10 }}>{question.media_type === 'video' ? 'Vidéo' : 'Photo'}</span>
                        : <span style={{ fontSize: 11, color: 'var(--muted)' }}>SVG interne</span>}
                      <button className="btn-sm btn-outline" style={{ marginLeft: 6, padding: '2px 8px', fontSize: 11 }} onClick={() => setEditing(question)}>Média</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <QuestionMediaModal
          question={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }}
        />
      )}
    </div>
  );
}

function QuestionMediaModal({ question, onClose, onSaved }: {
  question: ExamQuestion;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isRealMedia = question.media_type === 'image' || question.media_type === 'video';
  const [mediaType, setMediaType] = useState<MediaKind>(question.media_type === 'video' ? 'video' : 'image');
  const [url, setUrl] = useState(isRealMedia ? (question.media_url ?? '') : '');
  const [alt, setAlt] = useState(isRealMedia ? (question.media_alt ?? '') : '');
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [inspection, setInspection] = useState<MediaInspection | null>(null);
  const [policy, setPolicy] = useState<MediaUploadPolicy>(FALLBACK_MEDIA_POLICIES[mediaType]);

  const urlOk = urlAllowed(url);
  const canSave = Boolean(url.trim() && urlOk && alt.trim());

  useEffect(() => {
    setPolicy(FALLBACK_MEDIA_POLICIES[mediaType]);
    setInspection(null);
  }, [mediaType]);

  async function handleFile(file: File | undefined) {
    if (!file || uploading) return;
    setErr(null);
    setInspection(null);
    setUploading(true);
    try {
      const kind = detectMediaKind(file);
      const signed = await signMediaUpload(kind) as SignatureWithPolicy;
      const activePolicy = signed.policy ?? FALLBACK_MEDIA_POLICIES[kind];
      const inspected = await inspectMediaFile(file, kind, activePolicy);
      setMediaType(kind);
      setPolicy(activePolicy);
      setInspection(inspected);

      const secureUrl = await uploadToCloudinary(file, signed);
      setUrl(secureUrl);
      if (!alt.trim()) setAlt(file.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' '));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload impossible.';
      setErr(message.toLowerCase().includes('cloudinary')
        ? "L'hébergement média n'est pas configuré. Vérifiez les variables Cloudinary dans Render."
        : message);
    } finally {
      setUploading(false);
    }
  }

  async function save(clear: boolean) {
    if (saving) return;
    setSaving(true);
    setErr(null);
    try {
      await updateQuestionMedia(question.id, clear
        ? { media_url: null }
        : { media_type: mediaType, media_url: url.trim(), media_alt: alt.trim() });
      onSaved();
    } catch (error) {
      setErr(error instanceof Error ? error.message : 'Enregistrement impossible.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(13,33,55,.62)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
      onClick={onClose}
    >
      <div className="card" style={{ maxWidth: 620, width: '100%', maxHeight: '92vh', overflow: 'auto' }} onClick={event => event.stopPropagation()}>
        <div className="card-header">
          <div>
            <span className="card-title">Media Factory</span>
            <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 2 }}>Contrôle qualité avant transfert</div>
          </div>
          <button className="btn-sm btn-outline" onClick={onClose}>Fermer</button>
        </div>

        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14, lineHeight: 1.5 }}>{question.text}</p>

        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 8 }}>
            <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>Taille max</div>
              <strong>{formatBytes(policy.max_bytes)}</strong>
            </div>
            <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>Résolution recommandée</div>
              <strong>{policy.recommended_min_width ?? '—'}×{policy.recommended_min_height ?? '—'}</strong>
            </div>
            <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{mediaType === 'video' ? 'Durée max' : 'Livraison cible'}</div>
              <strong>{mediaType === 'video' ? `${policy.max_duration_seconds ?? 30} s` : (policy.delivery_formats ?? ['webp']).join(' / ')}</strong>
            </div>
          </div>

          <label>Type de média
            <select value={mediaType} onChange={event => setMediaType(event.target.value as MediaKind)}>
              <option value="image">Photo / image</option>
              <option value="video">Vidéo courte</option>
            </select>
          </label>

          <div style={{ border: '1.5px dashed var(--line)', borderRadius: 12, padding: '18px 14px', textAlign: 'center', background: 'var(--bg)' }}>
            <label style={{ cursor: uploading ? 'wait' : 'pointer', display: 'block' }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--guinea-green)' }}>
                {uploading ? 'Contrôle puis téléversement…' : 'Choisir une photo ou une vidéo'}
              </span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/avif,video/mp4,video/webm,video/quicktime"
                style={{ display: 'none' }}
                disabled={uploading}
                onChange={event => {
                  const file = event.target.files?.[0];
                  void handleFile(file);
                  event.currentTarget.value = '';
                }}
              />
              <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 5 }}>
                Validation locale de la taille, du format, des dimensions et de la durée avant envoi du fichier.
              </p>
            </label>
          </div>

          {inspection && (
            <div className="alert as" style={{ fontSize: 11.5 }}>
              <strong>Fichier contrôlé :</strong> {formatBytes(inspection.sizeBytes)} · {inspection.width ?? '—'}×{inspection.height ?? '—'}
              {inspection.kind === 'video' ? ` · ${humanDuration(inspection.durationSeconds)}` : ''}
              {inspection.warnings.map(warning => <div key={warning} style={{ marginTop: 4 }}>⚠ {warning}</div>)}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ flex: 1, height: 1, background: 'var(--line)' }} />
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>ou URL HTTPS existante</span>
            <div style={{ flex: 1, height: 1, background: 'var(--line)' }} />
          </div>

          <label>URL du média
            <input
              value={url}
              onChange={event => { setUrl(event.target.value); setInspection(null); }}
              autoComplete="off"
              placeholder="https://cdn.exemple.gn/media/question.webp"
            />
            {!urlOk && <span style={{ fontSize: 11, color: 'var(--red)', marginTop: 3, display: 'block' }}>HTTPS obligatoire hors localhost de développement.</span>}
          </label>

          <label>Description accessible (obligatoire)
            <input
              value={alt}
              onChange={event => setAlt(event.target.value)}
              autoComplete="off"
              placeholder="Ex. Intersection de Matam sous forte pluie, véhicule approchant un passage piéton"
            />
            {!alt.trim() && <span style={{ fontSize: 10.5, color: 'var(--muted)', display: 'block', marginTop: 3 }}>Le média ne peut pas être validé sans texte alternatif.</span>}
          </label>

          {url.trim() && urlOk && (
            <div style={{ borderRadius: 12, overflow: 'hidden', background: '#0b1725', border: '1px solid var(--border)' }}>
              <div style={{ padding: '7px 10px', color: 'rgba(255,255,255,.75)', fontSize: 10.5 }}>Aperçu 16:9</div>
              <div style={{ aspectRatio: '16 / 9', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000' }}>
                {mediaType === 'video'
                  ? <video src={url.trim()} controls preload="metadata" playsInline style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                  : <img src={url.trim()} alt={alt || 'Aperçu'} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />}
              </div>
            </div>
          )}

          <div className="alert ai" style={{ fontSize: 11.5 }}>
            Pour la banque officielle : privilégiez des scènes guinéennes réelles ou des illustrations contrôlées, sans plaque lisible ni visage identifiable sans autorisation.
          </div>

          {err && <div className="alert ae">{err}</div>}

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn-primary" style={{ flex: 1, minWidth: 180 }} disabled={saving || uploading || !canSave} onClick={() => { void save(false); }}>
              {saving ? 'Enregistrement…' : 'Associer ce média'}
            </button>
            {isRealMedia && <button className="btn-outline" disabled={saving || uploading} onClick={() => { void save(true); }}>Revenir au SVG</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
