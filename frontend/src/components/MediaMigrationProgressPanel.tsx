import { useState, type CSSProperties } from 'react';
import { getMediaMigrationProgress, type MediaMigrationProgress } from '../mediaProgressApi';

function Kpi({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <div style={s.kpi}>
      <span style={s.kpiLabel}>{label}</span>
      <strong style={s.kpiValue}>{value}</strong>
      <span style={s.muted}>{detail}</span>
    </div>
  );
}

export function MediaMigrationProgressPanel() {
  const [data, setData] = useState<MediaMigrationProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true); setError('');
    try {
      setData(await getMediaMigrationProgress());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Progression média indisponible');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section data-testid="media-migration-progress" style={s.shell}>
      <header style={s.header}>
        <div>
          <p style={s.eyebrow}>Pilotage de migration</p>
          <h2 style={{ margin: 0 }}>Progression vers les médias premium</h2>
          <p style={s.muted}>Le pourcentage “publiable” correspond au même quality gate que l’examen officiel.</p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => void refresh()} disabled={loading} data-testid="refresh-media-progress">
          {loading ? 'Calcul…' : 'Actualiser la progression'}
        </button>
      </header>

      {error && <div role="alert" style={s.error}>{error}</div>}

      {!data ? (
        <div style={s.empty}>Cliquez sur « Actualiser » pour mesurer l’état réel de la banque de questions.</div>
      ) : (
        <>
          <div style={s.progressWrap}>
            <div style={s.progressHeader}>
              <strong>{data.publishable_percent.toFixed(1)} % publiable premium</strong>
              <span style={s.muted}>{data.publishable_premium} / {data.total_questions} questions</span>
            </div>
            <div style={s.progressTrack} aria-label={`Progression média premium ${data.publishable_percent}%`}>
              <div style={{ ...s.progressBar, width: `${Math.max(0, Math.min(100, data.publishable_percent))}%` }} />
            </div>
          </div>

          <div style={s.grid}>
            <Kpi label="Questions totales" value={data.total_questions} detail="Banque actuellement mesurée" />
            <Kpi label="Primary normalisé" value={data.normalized_primary} detail={`${data.normalized_percent.toFixed(1)} % de la banque`} />
            <Kpi label="Publiables" value={data.publishable_premium} detail="Gate qualité + réglementaire complet" />
            <Kpi label="Normalisés bloqués" value={data.normalized_blocked} detail="À corriger ou revalider" />
            <Kpi label="Encore legacy" value={data.legacy_only} detail="Question.media_* sans primary normalisé" />
            <Kpi label="Sans média" value={data.no_media} detail="Ni primary ni média historique" />
            <Kpi label="Images primary" value={data.by_primary_type.image} detail="Médias normalisés image" />
            <Kpi label="Vidéos primary" value={data.by_primary_type.video} detail="Médias normalisés vidéo" />
          </div>

          {data.blocked_question_ids_sample.length > 0 && (
            <details style={s.details}>
              <summary>Exemple de questions normalisées encore bloquées</summary>
              <div style={s.chips}>
                {data.blocked_question_ids_sample.map(id => <code key={id} style={s.chip}>{id}</code>)}
              </div>
            </details>
          )}

          <p style={s.notice}>
            Cette métrique ne déclare aucune homologation institutionnelle. Elle mesure uniquement l’état technique et les validations enregistrées dans CodeRoute.
          </p>
        </>
      )}
    </section>
  );
}

const s: Record<string, CSSProperties> = {
  shell: { maxWidth: 1440, margin: '18px auto 40px', padding: 24, display: 'grid', gap: 16, border: '1px solid var(--border)', borderRadius: 18, background: 'var(--surface)', boxShadow: '0 8px 24px rgba(0,0,0,.04)' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' },
  eyebrow: { margin: 0, textTransform: 'uppercase', letterSpacing: '.08em', fontSize: 11, fontWeight: 800, color: 'var(--muted)' },
  muted: { margin: 0, color: 'var(--muted)', fontSize: 12, lineHeight: 1.45 },
  empty: { padding: 16, borderRadius: 12, background: 'var(--bg)', color: 'var(--muted)', fontSize: 12 },
  error: { padding: 12, borderRadius: 10, border: '1px solid var(--danger,#b91c1c)', color: 'var(--danger,#b91c1c)' },
  progressWrap: { display: 'grid', gap: 8 },
  progressHeader: { display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' },
  progressTrack: { height: 12, borderRadius: 999, background: 'var(--bg)', overflow: 'hidden', border: '1px solid var(--border)' },
  progressBar: { height: '100%', borderRadius: 999, background: 'linear-gradient(90deg,#16a34a,#22c55e)', transition: 'width .25s ease' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 10 },
  kpi: { display: 'grid', gap: 5, padding: 14, border: '1px solid var(--border)', borderRadius: 12, background: 'var(--bg)' },
  kpiLabel: { fontSize: 11, fontWeight: 800, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.04em' },
  kpiValue: { fontSize: 26, lineHeight: 1.1 },
  details: { borderTop: '1px solid var(--border)', paddingTop: 10, fontSize: 12 },
  chips: { display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 },
  chip: { padding: '4px 7px', borderRadius: 7, background: 'var(--bg)', border: '1px solid var(--border)', fontSize: 10 },
  notice: { margin: 0, padding: 10, borderRadius: 10, background: '#f8fafc', color: 'var(--muted)', fontSize: 11, lineHeight: 1.5 },
};
