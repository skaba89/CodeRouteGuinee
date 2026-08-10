import { useMemo, useState, type CSSProperties } from 'react';
import { useAuthSession } from '../authSession';
import {
  runMediaMigrationPlan,
  type MediaMigrationPlanMapping,
  type MediaMigrationPlanResult,
} from '../mediaMigrationPlanApi';

function parseMappings(raw: string): { mappings: MediaMigrationPlanMapping[]; errors: string[] } {
  const mappings: MediaMigrationPlanMapping[] = [];
  const errors: string[] = [];
  const seen = new Set<string>();

  raw.split(/\r?\n/).forEach((sourceLine, index) => {
    const line = sourceLine.trim();
    if (!line || line.startsWith('#')) return;
    const parts = line.split(/[;,\t]/).map(value => value.trim());
    if (index === 0 && parts[0]?.toLowerCase() === 'question_id' && parts[1]?.toLowerCase() === 'media_id') return;
    if (parts.length < 2 || !parts[0] || !parts[1]) {
      errors.push(`Ligne ${index + 1} : question_id et media_id sont obligatoires.`);
      return;
    }
    if (seen.has(parts[0])) {
      errors.push(`Ligne ${index + 1} : question ${parts[0]} dupliquée dans le lot.`);
      return;
    }
    seen.add(parts[0]);
    mappings.push({ question_id: parts[0], media_id: parts[1] });
  });

  if (mappings.length === 0 && errors.length === 0) errors.push('Ajoutez au moins une association question_id,media_id.');
  if (mappings.length > 500) errors.push('Un lot est limité à 500 associations.');
  return { mappings, errors };
}

function planFingerprint(raw: string, reason: string, replaceExisting: boolean): string {
  return JSON.stringify({ raw: raw.trim(), reason: reason.trim(), replaceExisting });
}

function StatusPill({ value }: { value: string }) {
  const good = value === 'ready_create' || value === 'ready_replace' || value === 'no_op';
  return <span style={{ ...s.status, color: good ? 'var(--success,#15803d)' : 'var(--danger,#b91c1c)' }}>{value}</span>;
}

export function MediaBatchMigrationWorkbench() {
  const { role } = useAuthSession();
  const isSuperAdmin = role === 'super_admin';
  const [rawPlan, setRawPlan] = useState('question_id,media_id\n');
  const [reason, setReason] = useState('Migration contrôlée des médias premium');
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [result, setResult] = useState<MediaMigrationPlanResult | null>(null);
  const [validatedFingerprint, setValidatedFingerprint] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const parsed = useMemo(() => parseMappings(rawPlan), [rawPlan]);
  const currentFingerprint = planFingerprint(rawPlan, reason, replaceExisting);
  const canApply = Boolean(
    result?.dry_run
      && result.all_ready
      && validatedFingerprint
      && validatedFingerprint === currentFingerprint
      && parsed.errors.length === 0
      && reason.trim().length >= 8
  );

  async function dryRun() {
    setError(''); setSuccess(''); setResult(null); setValidatedFingerprint('');
    if (parsed.errors.length > 0) { setError(parsed.errors.join(' ')); return; }
    if (reason.trim().length < 8) { setError('Le motif doit contenir au moins 8 caractères.'); return; }

    setBusy(true);
    try {
      const next = await runMediaMigrationPlan({
        dry_run: true,
        replace_existing: replaceExisting,
        reason: reason.trim(),
        mappings: parsed.mappings,
      });
      setResult(next);
      if (next.all_ready) {
        setValidatedFingerprint(currentFingerprint);
        setSuccess('Dry-run validé : le lot peut être appliqué sans mapping implicite.');
      } else {
        setError('Dry-run bloqué : corrigez toutes les lignes avant application.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dry-run impossible');
    } finally { setBusy(false); }
  }

  async function applyPlan() {
    setError(''); setSuccess('');
    if (!canApply) {
      setError('Le plan a changé ou n’a pas de dry-run 100 % prêt. Relancez le dry-run.');
      return;
    }

    setBusy(true);
    try {
      const applied = await runMediaMigrationPlan({
        dry_run: false,
        replace_existing: replaceExisting,
        reason: reason.trim(),
        mappings: parsed.mappings,
      });
      setResult(applied);
      setValidatedFingerprint('');
      setSuccess(`Migration appliquée : ${applied.applied} association(s) modifiée(s), transaction unique.`);
    } catch (err) {
      setValidatedFingerprint('');
      setError(err instanceof Error ? err.message : 'Application du lot impossible');
    } finally { setBusy(false); }
  }

  return (
    <section data-testid="media-batch-migration" style={s.shell}>
      <header style={s.header}>
        <div>
          <p style={s.eyebrow}>Industrialisation de la migration</p>
          <h2 style={{ margin: 0 }}>Plan question → média par lots</h2>
          <p style={s.muted}>Les identifiants sont fournis explicitement. Le serveur refuse tout le lot si une seule ligne échoue au quality gate officiel.</p>
        </div>
        <span style={s.badge}>Max 500 / transaction</span>
      </header>

      {error && <div role="alert" style={s.error}>{error}</div>}
      {success && <div role="status" style={s.success}>{success}</div>}

      <div style={s.columns}>
        <div style={s.panel}>
          <label style={s.label}>Plan CSV / point-virgule
            <textarea
              data-testid="media-migration-plan-input"
              rows={12}
              spellCheck={false}
              value={rawPlan}
              onChange={e => { setRawPlan(e.target.value); setValidatedFingerprint(''); }}
              placeholder={'question_id,media_id\nUUID-QUESTION,UUID-MEDIA'}
            />
          </label>
          <div style={s.hint}>Formats acceptés : virgule, point-virgule ou tabulation. En-tête facultatif. Commentaires avec #.</div>
          <div style={s.parseSummary}>
            <strong>{parsed.mappings.length} association(s) détectée(s)</strong>
            {parsed.errors.length > 0 && <span style={{ color: 'var(--danger,#b91c1c)' }}>{parsed.errors.length} erreur(s) locale(s)</span>}
          </div>
        </div>

        <div style={s.panel}>
          <label style={s.label}>Motif auditable
            <textarea rows={4} value={reason} onChange={e => { setReason(e.target.value); setValidatedFingerprint(''); }} />
          </label>
          {isSuperAdmin ? (
            <label style={s.checkbox}>
              <input type="checkbox" checked={replaceExisting} onChange={e => { setReplaceExisting(e.target.checked); setValidatedFingerprint(''); }} />
              Autoriser le remplacement d’un `primary` existant
            </label>
          ) : (
            <div style={s.notice}>Un admin peut uniquement créer les primary manquants. Le remplacement d’un primary existant exige un super_admin.</div>
          )}
          <div style={s.actions}>
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => void dryRun()} data-testid="dry-run-media-migration-plan">
              {busy ? 'Contrôle…' : '1. Dry-run complet'}
            </button>
            <button type="button" className="btn-primary" disabled={busy || !canApply} onClick={() => void applyPlan()} data-testid="apply-media-migration-plan">
              2. Appliquer le lot
            </button>
          </div>
          <p style={s.notice}>Toute modification du CSV, du motif ou de l’option de remplacement invalide le dry-run côté interface. Le serveur revalide également le plan avant écriture.</p>
        </div>
      </div>

      {result && (
        <div style={s.panel} data-testid="media-migration-plan-result">
          <div style={s.resultHeader}>
            <div>
              <strong>{result.dry_run ? 'Résultat du dry-run' : 'Résultat de l’application'}</strong>
              <p style={s.muted}>all_ready={String(result.all_ready)} · applied={result.applied}</p>
            </div>
            <div style={s.metrics}>
              {Object.entries(result.summary).map(([key, value]) => <span key={key} style={s.metric}>{key}: <strong>{value}</strong></span>)}
            </div>
          </div>

          <div style={s.results}>
            {result.items.map(item => (
              <div key={`${item.question_id}:${item.media_id}`} style={s.resultRow}>
                <div style={{ display: 'grid', gap: 4, minWidth: 0 }}>
                  <StatusPill value={item.status} />
                  <code style={s.code}>Q {item.question_id}</code>
                  <code style={s.code}>M {item.media_id}</code>
                  {item.existing_primary_media_id && <span style={s.muted}>Primary actuel : {item.existing_primary_media_id}</span>}
                </div>
                <div style={s.blockers}>
                  {item.blocker_codes.map(code => <code key={code} style={s.blocker}>{code}</code>)}
                </div>
              </div>
            ))}
          </div>
          <p style={s.notice}>Ce résultat ne constitue jamais une homologation DNTT. Il prouve uniquement que les associations passent les contrôles enregistrés dans la plateforme.</p>
        </div>
      )}
    </section>
  );
}

const s: Record<string, CSSProperties> = {
  shell: { maxWidth: 1440, margin: '18px auto 40px', padding: 24, display: 'grid', gap: 16, border: '1px solid var(--border)', borderRadius: 18, background: 'var(--surface)', boxShadow: '0 8px 24px rgba(0,0,0,.04)' },
  header: { display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' },
  eyebrow: { margin: 0, textTransform: 'uppercase', letterSpacing: '.08em', fontSize: 11, fontWeight: 800, color: 'var(--muted)' },
  muted: { margin: 0, color: 'var(--muted)', fontSize: 12, lineHeight: 1.5 },
  badge: { padding: '5px 9px', border: '1px solid var(--border)', borderRadius: 999, fontSize: 11, fontWeight: 700 },
  columns: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 14 },
  panel: { padding: 16, border: '1px solid var(--border)', borderRadius: 16, background: 'var(--bg)', display: 'grid', gap: 12 },
  label: { display: 'grid', gap: 6, fontSize: 12, fontWeight: 700 },
  checkbox: { display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, fontWeight: 700 },
  hint: { color: 'var(--muted)', fontSize: 11 },
  parseSummary: { display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'space-between', fontSize: 12 },
  actions: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  notice: { margin: 0, padding: 10, borderRadius: 10, background: 'var(--surface)', color: 'var(--muted)', fontSize: 11, lineHeight: 1.5 },
  error: { padding: 12, borderRadius: 10, border: '1px solid var(--danger,#b91c1c)', color: 'var(--danger,#b91c1c)' },
  success: { padding: 12, borderRadius: 10, border: '1px solid var(--success,#15803d)', color: 'var(--success,#15803d)' },
  resultHeader: { display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' },
  metrics: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  metric: { padding: '4px 7px', border: '1px solid var(--border)', borderRadius: 999, fontSize: 10 },
  results: { display: 'grid', gap: 8, maxHeight: 480, overflow: 'auto' },
  resultRow: { display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', padding: 10, borderRadius: 10, background: 'var(--surface)' },
  status: { width: 'fit-content', fontSize: 10, fontWeight: 800, textTransform: 'uppercase' },
  code: { fontSize: 9, color: 'var(--muted)', overflowWrap: 'anywhere' },
  blockers: { display: 'flex', gap: 5, flexWrap: 'wrap', alignItems: 'center' },
  blocker: { padding: '3px 6px', borderRadius: 7, background: '#fff7ed', color: '#9a3412', fontSize: 9 },
};
