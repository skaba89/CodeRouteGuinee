import { useState, type CSSProperties } from 'react';
import { getQuestions, type ExamQuestion } from '../api';
import { listMediaAssets, type MediaAsset } from '../mediaApi';
import {
  linkQuestionMedia,
  listQuestionMedia,
  unlinkQuestionMedia,
  type QuestionMediaLink,
  type QuestionMediaRole,
} from '../mediaQuestionApi';

function short(value: string, length = 88): string {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function mediaUrl(asset: MediaAsset): string | null {
  return asset.secure_url || asset.public_url || null;
}

export function MediaQuestionMappingWorkbench() {
  const [questionSearch, setQuestionSearch] = useState('');
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<ExamQuestion | null>(null);
  const [mediaSearch, setMediaSearch] = useState('');
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<MediaAsset | null>(null);
  const [links, setLinks] = useState<QuestionMediaLink[]>([]);
  const [role, setRole] = useState<QuestionMediaRole>('primary');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function searchQuestions() {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await getQuestions({ limit: 25, search: questionSearch || undefined });
      setQuestions(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recherche de questions impossible');
    } finally { setBusy(false); }
  }

  async function searchAssets() {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await listMediaAssets({
        limit: 50,
        search: mediaSearch || undefined,
        quality_status: 'validated',
        regulatory_status: role === 'primary' ? 'validated' : undefined,
      });
      setAssets(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recherche de médias impossible');
    } finally { setBusy(false); }
  }

  async function selectQuestion(question: ExamQuestion) {
    setSelectedQuestion(question);
    setSelectedAsset(null);
    setNotice(''); setError('');
    try { setLinks(await listQuestionMedia(question.id)); }
    catch (err) { setError(err instanceof Error ? err.message : 'Associations impossibles à charger'); }
  }

  async function attach() {
    if (!selectedQuestion || !selectedAsset) return;
    if (role === 'primary') {
      if (selectedAsset.quality_status !== 'validated' || selectedAsset.regulatory_status !== 'validated') {
        setError('Un média principal d’examen doit être validé en qualité et réglementairement.');
        return;
      }
      if (selectedAsset.usage_type !== 'exam') {
        setError('Le média principal doit avoir usage_type=exam.');
        return;
      }
    }

    setBusy(true); setError(''); setNotice('');
    try {
      await linkQuestionMedia(selectedQuestion.id, selectedAsset.id, role, 0);
      setLinks(await listQuestionMedia(selectedQuestion.id));
      setNotice(`Média associé à la question comme ${role}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Association impossible');
    } finally { setBusy(false); }
  }

  async function detach(link: QuestionMediaLink) {
    if (!selectedQuestion) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await unlinkQuestionMedia(selectedQuestion.id, link.id);
      setLinks(await listQuestionMedia(selectedQuestion.id));
      setNotice(`Association ${link.role} supprimée.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dissociation impossible');
    } finally { setBusy(false); }
  }

  return (
    <section data-testid="media-question-mapping" style={s.shell}>
      <header style={s.header}>
        <div>
          <p style={s.eyebrow}>Migration contrôlée</p>
          <h2 style={{ margin: 0 }}>Associer les médias aux bonnes questions</h2>
          <p style={s.muted}>Aucun mapping automatique : chaque association est explicite, auditée et réversible.</p>
        </div>
        <span style={s.badge}>Question ↔ MediaAsset</span>
      </header>

      {error && <div role="alert" style={s.error}>{error}</div>}
      {notice && <div role="status" style={s.success}>{notice}</div>}

      <div style={s.columns}>
        <div style={s.panel}>
          <strong>1. Choisir la question</strong>
          <div style={s.searchRow}>
            <input value={questionSearch} onChange={e => setQuestionSearch(e.target.value)} placeholder="Texte ou catégorie…" aria-label="Rechercher une question" />
            <button className="btn-secondary" type="button" disabled={busy} onClick={() => void searchQuestions()}>Rechercher</button>
          </div>
          <div style={s.list}>
            {questions.map(question => (
              <button
                key={question.id}
                type="button"
                onClick={() => void selectQuestion(question)}
                style={{ ...s.item, ...(selectedQuestion?.id === question.id ? s.selected : {}) }}
                data-testid={`mapping-question-${question.id}`}
              >
                <span style={s.itemTitle}>{question.category}</span>
                <span style={s.itemText}>{short(question.text)}</span>
                <code style={s.code}>{question.id}</code>
              </button>
            ))}
            {questions.length === 0 && <span style={s.muted}>Lancez une recherche pour sélectionner une question.</span>}
          </div>
        </div>

        <div style={s.panel}>
          <strong>2. Choisir le média validé</strong>
          <div style={s.searchRow}>
            <input value={mediaSearch} onChange={e => setMediaSearch(e.target.value)} placeholder="Thème, source…" aria-label="Rechercher un média validé" />
            <button className="btn-secondary" type="button" disabled={busy} onClick={() => void searchAssets()}>Rechercher</button>
          </div>
          <div style={s.roleRow}>
            <label style={s.label}>Rôle
              <select value={role} onChange={e => { setRole(e.target.value as QuestionMediaRole); setAssets([]); }}>
                <option value="primary">Primary — examen</option>
                <option value="explanation">Explanation — correction</option>
              </select>
            </label>
          </div>
          <div style={s.list}>
            {assets.map(asset => {
              const url = mediaUrl(asset);
              return (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => setSelectedAsset(asset)}
                  style={{ ...s.item, ...(selectedAsset?.id === asset.id ? s.selected : {}) }}
                  data-testid={`mapping-media-${asset.id}`}
                >
                  {url && asset.media_type === 'image' && <img src={url} alt="Miniature média" loading="lazy" style={s.thumb} />}
                  <span style={s.itemTitle}>{asset.theme || 'Sans thème'} · {asset.media_type}</span>
                  <span style={s.itemText}>{asset.quality_status} / {asset.regulatory_status}</span>
                  <code style={s.code}>{asset.id}</code>
                </button>
              );
            })}
            {assets.length === 0 && <span style={s.muted}>Les médias `primary` sont filtrés sur qualité + validation réglementaire.</span>}
          </div>
        </div>
      </div>

      <div style={s.panel}>
        <div style={s.linkHeader}>
          <div>
            <strong>3. Valider l’association</strong>
            <p style={s.muted}>{selectedQuestion ? short(selectedQuestion.text, 120) : 'Aucune question sélectionnée'}</p>
          </div>
          <button className="btn-primary" type="button" disabled={busy || !selectedQuestion || !selectedAsset} onClick={() => void attach()} data-testid="attach-question-media">
            Associer comme {role}
          </button>
        </div>

        {selectedAsset?.media_type === 'video' && role === 'primary' && (
          <p style={s.warning}>
            Vidéo officielle : le quality gate exige aussi `poster_media_id` et `fallback_media_id` validés sur le MediaAsset vidéo. Cette association ne contourne jamais ce contrôle.
          </p>
        )}

        <div style={s.links}>
          {links.map(link => (
            <div key={link.id} style={s.linkRow}>
              <div><strong>{link.role}</strong><div style={s.muted}>{link.media_id}</div></div>
              <button className="btn-secondary" type="button" disabled={busy} onClick={() => void detach(link)}>Dissocier</button>
            </div>
          ))}
          {selectedQuestion && links.length === 0 && <span style={s.muted}>Aucun média normalisé associé à cette question.</span>}
        </div>
      </div>
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
  roleRow: { display: 'flex', gap: 8 },
  label: { display: 'grid', gap: 5, fontSize: 12, fontWeight: 700 },
  list: { display: 'grid', gap: 8, maxHeight: 340, overflow: 'auto' },
  item: { display: 'grid', gap: 4, textAlign: 'left', padding: 10, border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)', color: 'inherit', cursor: 'pointer' },
  selected: { outline: '2px solid var(--primary)', outlineOffset: 1 },
  itemTitle: { fontWeight: 800, fontSize: 12 },
  itemText: { fontSize: 12, color: 'var(--text)' },
  code: { fontSize: 9, color: 'var(--muted)', overflowWrap: 'anywhere' },
  thumb: { width: '100%', aspectRatio: '16/9', objectFit: 'cover', borderRadius: 7, background: 'var(--bg)' },
  linkHeader: { display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' },
  links: { display: 'grid', gap: 8 },
  linkRow: { display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', padding: 10, borderRadius: 10, background: 'var(--bg)' },
  warning: { margin: 0, padding: 10, borderRadius: 10, background: '#fff7ed', color: '#9a3412', fontSize: 11, lineHeight: 1.5 },
  error: { padding: 12, borderRadius: 10, border: '1px solid var(--danger,#b91c1c)', color: 'var(--danger,#b91c1c)' },
  success: { padding: 12, borderRadius: 10, border: '1px solid var(--success,#15803d)', color: 'var(--success,#15803d)' },
};
