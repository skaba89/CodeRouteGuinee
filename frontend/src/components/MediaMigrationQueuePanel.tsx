import { useState, type CSSProperties } from 'react';
import {
  getMediaMigrationQueue,
  type MediaMigrationQueueItem,
  type MediaMigrationQueueResponse,
  type MediaMigrationQueueState,
} from '../mediaQueueApi';

export type MediaQueueQuestionRef = Pick<MediaMigrationQueueItem, 'question_id' | 'text' | 'category'>;

const STATE_LABELS: Record<string, string> = {
  publishable: 'Publiable premium',
  normalized_blocked: 'Normalisé bloqué',
  legacy_only: 'Legacy à migrer',
  no_media: 'Sans média',
};

function tone(state: string): string {
  if (state === 'publishable') return 'var(--success,#15803d)';
  if (state === 'normalized_blocked') return 'var(--danger,#b91c1c)';
  if (state === 'no_media') return 'var(--warning,#a16207)';
  return 'var(--muted)';
}

function short(value: string, length = 170): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

export function MediaMigrationQueuePanel({ onMapQuestion }: { onMapQuestion?: (question: MediaQueueQuestionRef) => void }) {
  const [data, setData] = useState<MediaMigrationQueueResponse | null>(null);
  const [stateFilter, setStateFilter] = useState<MediaMigrationQueueState>('needs_action');
  const [questionStatus, setQuestionStatus] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true); setError('');
    try {
      setData(await getMediaMigrationQueue({
        state_filter: stateFilter,
        question_status: questionStatus || undefined,
        search: search || undefined,
        limit: 100,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'File de migration indisponible');
    } finally {
      setLoading(false);
    }
  }

  function treat(item: MediaMigrationQueueItem) {
    onMapQuestion?.({ question_id: item.question_id, text: item.text, category: item.category });
    window.requestAnimationFrame(() => {
      document.querySelector('[data-testid="media-question-mapping"]')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  return (
    <section data-testid="media-migration-queue" style={s.shell}>
      <header style={s.header}>
        <div>
          <p style={s.eyebrow}>Plan de migration actionnable</p>
          <h2 style={{ margin: 0 }}>File des questions à traiter</h2>
          <p style={s.muted}>Priorité aux questions déjà approuvées. Aucun média n’est choisi automatiquement.</p>
        </div>
        <button type="button" className="btn-secondary" disabled={loading} onClick={() => void refresh()} data-testid="refresh-media-queue">
          {loading ? 'Analyse…' : 'Actualiser la file'}
        </button>
      </header>

      <div style={s.filters}>
        <label style={s.label}>État
          <select value={stateFilter} onChange={e => setStateFilter(e.target.value as MediaMigrationQueueState)}>
            <option value="needs_action">À traiter</option>
            <option value="normalized_blocked">Normalisés bloqués</option>
            <option value="legacy_only">Legacy</option>
            <option value="no_media">Sans média</option>
            <option value="publishable">Publiables</option>
            <option value="all">Tous</option>
          </select>
        </label>
        <label style={s.label}>Statut question
          <select value={questionStatus} onChange={e => setQuestionStatus(e.target.value)}>
            <option value="">Tous</option>
            <option value="approved">Approved</option>
            <option value="submitted">Submitted</option>
            <option value="draft">Draft</option>
            <option value="rejected">Rejected</option>
          </select>
        </label>
        <label style={{ ...s.label, flex: '1 1 260px' }}>Recherche
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Texte ou catégorie…" onKeyDown={e => { if (e.key === 'Enter') void refresh(); }} />
        </label>
      </div>

      {error && <div role="alert" style={s.error}>{error}</div>}

      {data && (
        <>
          <div style={s.counts}>
            <span style={s.chip}>Bloqués <strong>{data.counts_by_state.normalized_blocked}</strong></span>
            <span style={s.chip}>Legacy <strong>{data.counts_by_state.legacy_only}</strong></span>
            <span style={s.chip}>Sans média <strong>{data.counts_by_state.no_media}</strong></span>
            <span style={s.chip}>Publiables <strong>{data.counts_by_state.publishable}</strong></span>
            <span style={s.chip}>Affichés <strong>{data.total}</strong></span>
          </div>

          <div style={s.list}>
            {data.items.map(item => (
              <article key={item.question_id} style={s.card} data-testid={`migration-queue-${item.question_id}`}>
                <div style={s.cardTop}>
                  <div style={{ display: 'grid', gap: 5, minWidth: 0 }}>
                    <div style={s.meta}>
                      <span style={{ ...s.state, color: tone(item.queue_state), borderColor: tone(item.queue_state) }}>{STATE_LABELS[item.queue_state] ?? item.queue_state}</span>
                      <span>{item.category}</span>
                      <span>Question : {item.validation_status}</span>
                      {item.priority === 'official_first' && <strong style={s.urgent}>Priorité examen officiel</strong>}
                    </div>
                    <strong>{short(item.text)}</strong>
                    <code style={s.code}>{item.question_id}</code>
                  </div>
                  {item.queue_state !== 'publishable' && (
                    <button type="button" className="btn-primary" onClick={() => treat(item)} data-testid={`treat-media-question-${item.question_id}`}>
                      Traiter cette question
                    </button>
                  )}
                </div>

                <div style={s.action}>{item.next_action}</div>

                {item.primary_media && (
                  <div style={s.mediaRow}>
                    <span>Primary : <code>{item.primary_media.id}</code></span>
                    <span>{item.primary_media.media_type}</span>
                    <span>{item.primary_media.theme || 'Sans thème'}</span>
                    <span>{item.primary_media.quality_status} / {item.primary_media.regulatory_status}</span>
                  </div>
                )}

                {item.blocker_codes.length > 0 && (
                  <details style={s.details}>
                    <summary>Blockers du quality gate ({item.blocker_codes.length})</summary>
                    <div style={s.blockers}>
                      {item.blocker_codes.map(code => <code key={code} style={s.blocker}>{code}</code>)}
                    </div>
                    {item.blocker_details.length > 0 && <ul style={s.detailList}>{item.blocker_details.map(detail => <li key={detail}>{detail}</li>)}</ul>}
                  </details>
                )}
              </article>
            ))}
            {data.items.length === 0 && <div style={s.empty}>Aucune question dans ce filtre.</div>}
          </div>

          <p style={s.notice}>
            Cette file réutilise le quality gate de l’examen officiel et ne déclare aucune homologation institutionnelle.
          </p>
        </>
      )}

      {!data && <div style={s.empty}>Cliquez sur « Actualiser la file » pour calculer les actions à mener.</div>}
    </section>
  );
}

const s: Record<string, CSSProperties> = {
  shell: { maxWidth: 1440, margin: '18px auto 40px', padding: 24, display: 'grid', gap: 16, border: '1px solid var(--border)', borderRadius: 18, background: 'var(--surface)', boxShadow: '0 8px 24px rgba(0,0,0,.04)' },
  header: { display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' },
  eyebrow: { margin: 0, textTransform: 'uppercase', letterSpacing: '.08em', fontSize: 11, fontWeight: 800, color: 'var(--muted)' },
  muted: { margin: 0, color: 'var(--muted)', fontSize: 12, lineHeight: 1.5 },
  filters: { display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'end' },
  label: { display: 'grid', gap: 5, fontSize: 12, fontWeight: 700 },
  counts: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  chip: { padding: '5px 8px', border: '1px solid var(--border)', borderRadius: 999, fontSize: 11 },
  list: { display: 'grid', gap: 10 },
  card: { display: 'grid', gap: 10, padding: 14, border: '1px solid var(--border)', borderRadius: 14, background: 'var(--bg)' },
  cardTop: { display: 'flex', justifyContent: 'space-between', gap: 14, alignItems: 'flex-start', flexWrap: 'wrap' },
  meta: { display: 'flex', gap: 7, flexWrap: 'wrap', alignItems: 'center', color: 'var(--muted)', fontSize: 11 },
  state: { border: '1px solid currentColor', borderRadius: 999, padding: '2px 6px', fontWeight: 800 },
  urgent: { color: 'var(--danger,#b91c1c)' },
  code: { fontSize: 9, color: 'var(--muted)', overflowWrap: 'anywhere' },
  action: { padding: 9, borderRadius: 9, background: 'var(--surface)', fontSize: 12, lineHeight: 1.5 },
  mediaRow: { display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 11, color: 'var(--muted)' },
  details: { fontSize: 12 },
  blockers: { display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 9 },
  blocker: { padding: '3px 6px', borderRadius: 7, background: '#fff7ed', color: '#9a3412', fontSize: 10 },
  detailList: { margin: '8px 0 0', paddingLeft: 18, color: 'var(--muted)', fontSize: 11, lineHeight: 1.5 },
  notice: { margin: 0, padding: 10, borderRadius: 10, background: '#f8fafc', color: 'var(--muted)', fontSize: 11, lineHeight: 1.5 },
  empty: { padding: 16, borderRadius: 12, background: 'var(--bg)', color: 'var(--muted)', fontSize: 12 },
  error: { padding: 12, borderRadius: 10, border: '1px solid var(--danger,#b91c1c)', color: 'var(--danger,#b91c1c)' },
};
