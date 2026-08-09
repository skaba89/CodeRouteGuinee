import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { canUseProtectedActions, useAuthSession } from '../authSession';
import {
  activateNationalPolicy,
  approveNationalPolicy,
  createHomologationDossier,
  createNationalPolicy,
  getGovernanceReadiness,
  getHomologationDossiers,
  getNationalPolicies,
  getTechnicalContract,
  submitNationalPolicy,
  type GovernanceReadiness,
  type GovernanceRecord,
  type HomologationDocument,
  type PolicyDocument,
  type TechnicalContract,
} from '../nationalGovernanceClient';

const CHECK_LABELS: Record<string, string> = {
  active_policy: 'Politique DNTT active',
  runtime_alignment: 'Runtime aligné',
  official_question_bank: 'Banque officielle',
  accredited_centers: 'Centres accrédités',
  backup_off_region: 'Backup hors région',
  restore_drill: 'Restore drill',
  pitr_provider: 'PITR fournisseur',
  api_failover: 'Failover API',
};

function statusBadge(value: string): string {
  if (value === 'active' || value === 'homologated' || value === 'pass') return 'bg';
  if (value === 'approved' || value === 'ready_for_decision' || value === 'pending_approval') return 'bgo';
  if (value === 'revoked' || value === 'rejected' || value === 'fail') return 'br';
  return 'bgr';
}

function fmtDate(value?: string | null): string {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString('fr-FR');
}

export function NationalGovernancePanel() {
  const { currentUser } = useAuthSession();
  const canWrite = canUseProtectedActions(currentUser, false, ['admin', 'super_admin']);
  const isSuperAdmin = canUseProtectedActions(currentUser, false, ['super_admin']);
  const [readiness, setReadiness] = useState<GovernanceReadiness | null>(null);
  const [contract, setContract] = useState<TechnicalContract | null>(null);
  const [policies, setPolicies] = useState<Array<GovernanceRecord<PolicyDocument>>>([]);
  const [dossiers, setDossiers] = useState<Array<GovernanceRecord<HomologationDocument>>>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [code, setCode] = useState('OFFICIAL_EXAM_CATEGORY_B');
  const [version, setVersion] = useState('2026.1');
  const [title, setTitle] = useState('Règles officielles — examen théorique Catégorie B');
  const [legalRef, setLegalRef] = useState('');
  const [legalTitle, setLegalTitle] = useState('');
  const [rationale, setRationale] = useState('Formalisation des paramètres validés par la DNTT avant activation nationale.');
  const [approvalNote, setApprovalNote] = useState('Validation institutionnelle après revue du dossier et des références.');
  const [dossierTitle, setDossierTitle] = useState('Dossier d’homologation nationale CodeRoute Guinée');

  async function load() {
    setLoading(true);
    try {
      const [nextReadiness, nextContract, nextPolicies, nextDossiers] = await Promise.all([
        getGovernanceReadiness(),
        getTechnicalContract(),
        getNationalPolicies(),
        getHomologationDossiers(),
      ]);
      setReadiness(nextReadiness);
      setContract(nextContract);
      setPolicies(nextPolicies);
      setDossiers(nextDossiers);
      setMessage(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Gouvernance nationale indisponible.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const active = readiness?.active_policy ?? null;
  const blockerLabels = useMemo(
    () => (readiness?.blockers ?? []).map(codeValue => CHECK_LABELS[codeValue] ?? codeValue),
    [readiness],
  );

  async function handleCreatePolicy(event: FormEvent) {
    event.preventDefault();
    if (!canWrite || !contract) return;
    if (!legalRef.trim() || !legalTitle.trim()) {
      setMessage('Référence et intitulé juridique/institutionnel obligatoires.');
      return;
    }
    setBusy('create-policy'); setMessage(null);
    try {
      await createNationalPolicy({
        code: code.trim().toUpperCase(),
        version: version.trim(),
        title: title.trim(),
        authority: 'DNTT',
        parameters: { ...contract.runtime, retake_cooldown_hours: contract.runtime.retake_cooldown_hours ?? 0 },
        legal_references: [{ reference: legalRef.trim(), title: legalTitle.trim(), source_ref: 'Dossier institutionnel DNTT' }],
        rationale: rationale.trim(),
      });
      setMessage('Draft de politique créé à partir du contrat technique courant. Il doit être soumis puis approuvé par deux acteurs distincts.');
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Création de politique impossible.');
    } finally { setBusy(null); }
  }

  async function act(key: string, action: () => Promise<unknown>, success: string) {
    setBusy(key); setMessage(null);
    try {
      await action();
      setMessage(success);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Action institutionnelle refusée.');
    } finally { setBusy(null); }
  }

  async function handleCreateDossier() {
    if (!canWrite || !active) return;
    await act(
      'create-dossier',
      () => createHomologationDossier({ title: dossierTitle.trim(), policy_reference: active.reference, target_scope: 'national' }),
      'Dossier d’homologation créé. Les cinq preuves institutionnelles doivent maintenant être rattachées côté API/workflow DNTT.',
    );
  }

  return (
    <div className="card" data-testid="national-governance-panel">
      <div className="card-header" style={{ alignItems: 'flex-start', gap: 14 }}>
        <div>
          <span className="card-title">Homologation nationale — DNTT</span>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
            Versionnement réglementaire · quatre yeux · alignement runtime · preuves de résilience · décision traçable
          </div>
        </div>
        {readiness && (
          <span className={`badge ${readiness.go_live_allowed ? 'bg' : 'br'}`} data-testid="national-go-live-status">
            {readiness.go_live_allowed ? 'Éligible au dossier' : 'Go-live bloqué'}
          </span>
        )}
      </div>

      {message && <div className="alert aw" style={{ marginBottom: 14 }}>{message}</div>}
      {loading && <p style={{ color: 'var(--muted)' }}>Chargement de la gouvernance nationale…</p>}

      {!loading && readiness && contract && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(175px,1fr))', gap: 10, marginBottom: 16 }}>
            <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase' }}>Politique active</div>
              <div style={{ fontSize: 17, fontWeight: 850, marginTop: 5 }}>{active ? `${active.document.code} · ${active.document.version}` : 'Aucune'}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{active?.reference ?? 'Activation institutionnelle requise'}</div>
            </div>
            <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase' }}>Contrat technique</div>
              <div style={{ fontSize: 17, fontWeight: 850, marginTop: 5 }}>{contract.runtime.question_count} Q · seuil {contract.runtime.pass_threshold}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{contract.runtime.duration_minutes} min · runtime courant</div>
            </div>
            <div style={{ border: `1px solid ${contract.alignment.aligned ? 'var(--border)' : '#fca5a5'}`, borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase' }}>Alignement</div>
              <div style={{ fontSize: 17, fontWeight: 850, marginTop: 5, color: contract.alignment.aligned ? 'var(--guinea-green)' : 'var(--red)' }}>
                {contract.alignment.aligned ? 'Conforme' : 'Dérive détectée'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{contract.alignment.drift.length} différence(s)</div>
            </div>
            <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase' }}>Dossiers</div>
              <div style={{ fontSize: 17, fontWeight: 850, marginTop: 5 }}>{dossiers.length}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{dossiers.filter(item => item.status === 'homologated').length} homologué(s)</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 8, marginBottom: 16 }}>
            {readiness.checks.map(check => (
              <div key={check.code} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: '10px 12px', display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 700 }}>{CHECK_LABELS[check.code] ?? check.code}</span>
                <span className={`badge ${statusBadge(check.status)}`}>{check.status === 'pass' ? 'OK' : 'Bloquant'}</span>
              </div>
            ))}
          </div>

          {blockerLabels.length > 0 && (
            <div className="alert aw" data-testid="homologation-blockers" style={{ marginBottom: 16 }}>
              <strong>Homologation nationale non autorisée :</strong> {blockerLabels.join(' · ')}
            </div>
          )}

          <div style={{ fontWeight: 800, marginBottom: 8 }}>Versions de politique DNTT</div>
          <div className="table-wrap" style={{ marginBottom: 18 }}>
            <table>
              <thead><tr><th>Référence</th><th>Version</th><th>Paramètres</th><th>Approbations</th><th>Statut</th><th>Empreinte</th><th>Action</th></tr></thead>
              <tbody>
                {policies.map(policy => (
                  <tr key={policy.reference}>
                    <td><strong>{policy.reference}</strong><br /><span style={{ fontSize: 11, color: 'var(--muted)' }}>{policy.title}</span></td>
                    <td>{policy.document.version}</td>
                    <td>{policy.document.parameters.question_count} Q · {policy.document.parameters.pass_threshold}/{policy.document.parameters.question_count} · {policy.document.parameters.duration_minutes} min</td>
                    <td>{policy.document.approvals?.length ?? 0}/2</td>
                    <td><span className={`badge ${statusBadge(policy.status)}`}>{policy.status}</span></td>
                    <td><code style={{ fontSize: 10.5 }}>{policy.document.document_sha256.slice(0, 12)}…</code></td>
                    <td>
                      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                        {canWrite && policy.status === 'draft' && <button className="secondary-button btn-sm" disabled={busy !== null} onClick={() => void act(`submit-${policy.reference}`, () => submitNationalPolicy(policy.reference), 'Politique soumise à approbation.')}>Soumettre</button>}
                        {canWrite && (policy.status === 'pending_approval' || policy.status === 'approved') && (policy.document.approvals?.length ?? 0) < 2 && <button className="secondary-button btn-sm" disabled={busy !== null} onClick={() => void act(`approve-${policy.reference}`, () => approveNationalPolicy(policy.reference, approvalNote), 'Approbation enregistrée.')}>Approuver</button>}
                        {isSuperAdmin && policy.status === 'approved' && <button className="btn-primary btn-sm" disabled={busy !== null} onClick={() => void act(`activate-${policy.reference}`, () => activateNationalPolicy(policy.reference), 'Politique activée après contrôle d’alignement.')}>Activer</button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {policies.length === 0 && <div style={{ color: 'var(--muted)', marginBottom: 18 }}>Aucune politique DNTT versionnée.</div>}

          {canWrite && (
            <details style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, marginBottom: 16 }}>
              <summary style={{ cursor: 'pointer', fontWeight: 800 }}>Créer un draft à partir du runtime courant</summary>
              <form onSubmit={handleCreatePolicy} style={{ display: 'grid', gap: 10, marginTop: 14 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10 }}>
                  <label>Code<input value={code} onChange={event => setCode(event.target.value)} /></label>
                  <label>Version<input value={version} onChange={event => setVersion(event.target.value)} placeholder="2026.1" /></label>
                  <label>Titre<input value={title} onChange={event => setTitle(event.target.value)} /></label>
                  <label>Référence juridique / décision<input value={legalRef} onChange={event => setLegalRef(event.target.value)} placeholder="Référence DNTT / arrêté / décision" /></label>
                  <label>Intitulé de la référence<input value={legalTitle} onChange={event => setLegalTitle(event.target.value)} /></label>
                </div>
                <label>Rationale<textarea rows={3} value={rationale} onChange={event => setRationale(event.target.value)} /></label>
                <label>Note d'approbation par défaut<textarea rows={2} value={approvalNote} onChange={event => setApprovalNote(event.target.value)} /></label>
                <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                  Le draft reprend automatiquement le runtime {contract.runtime.question_count} questions / seuil {contract.runtime.pass_threshold} / {contract.runtime.duration_minutes} minutes. Toute autre règle doit être modifiée et testée côté backend avant activation.
                </div>
                <button className="btn-primary" type="submit" disabled={busy !== null}>{busy === 'create-policy' ? 'Création…' : 'Créer le draft DNTT'}</button>
              </form>
            </details>
          )}

          <div style={{ fontWeight: 800, marginBottom: 8 }}>Dossiers d’homologation</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {dossiers.map(dossier => (
              <div key={dossier.reference} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 12, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <strong>{dossier.reference}</strong>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>
                    {dossier.document.policy_reference} · {Object.keys(dossier.document.evidence ?? {}).length}/5 preuves · créé {fmtDate(dossier.created_at)}
                  </div>
                </div>
                <span className={`badge ${statusBadge(dossier.status)}`}>{dossier.status}</span>
              </div>
            ))}
            {dossiers.length === 0 && <div style={{ color: 'var(--muted)' }}>Aucun dossier d’homologation.</div>}
          </div>

          {canWrite && active && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'end', marginTop: 12, flexWrap: 'wrap' }}>
              <label style={{ flex: '1 1 340px' }}>Titre du dossier<input value={dossierTitle} onChange={event => setDossierTitle(event.target.value)} /></label>
              <button type="button" className="secondary-button" disabled={busy !== null} onClick={() => void handleCreateDossier()}>
                {busy === 'create-dossier' ? 'Création…' : 'Ouvrir un dossier national'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
