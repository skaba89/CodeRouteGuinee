import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { canUseProtectedActions, useAuthSession } from '../authSession';
import {
  approveHomologationDossier,
  attachHomologationEvidence,
  decideHomologationDossier,
  getHomologationDossiers,
  submitHomologationDossier,
  type GovernanceRecord,
  type HomologationDocument,
  type HomologationEvidence,
  type HomologationEvidenceCode,
} from '../nationalGovernanceClient';

const EVIDENCE_LABELS: Record<HomologationEvidenceCode, string> = {
  dntt_exam_rules: 'Règles officielles DNTT',
  legal_review: 'Revue juridique',
  security_assessment: 'Évaluation sécurité',
  operations_readiness: 'Readiness exploitation',
  content_signoff: 'Validation contenus',
};

const EVIDENCE_CODES = Object.keys(EVIDENCE_LABELS) as HomologationEvidenceCode[];
const SHA256_RE = /^[a-fA-F0-9]{64}$/;

function badge(status: string): string {
  if (status === 'homologated') return 'bg';
  if (status === 'ready_for_decision' || status === 'pending_approval') return 'bgo';
  if (status === 'rejected') return 'br';
  return 'bgr';
}

function hasValidHash(evidence: HomologationEvidence | undefined): boolean {
  return Boolean(evidence?.artifact_sha256 && SHA256_RE.test(evidence.artifact_sha256));
}

function validEvidenceCount(document: HomologationDocument): number {
  return EVIDENCE_CODES.filter(code => hasValidHash(document.evidence?.[code])).length;
}

export function NationalHomologationEvidencePanel() {
  const { currentUser } = useAuthSession();
  const canWrite = canUseProtectedActions(currentUser, false, ['admin', 'super_admin']);
  const isSuperAdmin = canUseProtectedActions(currentUser, false, ['super_admin']);
  const [dossiers, setDossiers] = useState<Array<GovernanceRecord<HomologationDocument>>>([]);
  const [selectedReference, setSelectedReference] = useState('');
  const [code, setCode] = useState<HomologationEvidenceCode>('dntt_exam_rules');
  const [evidenceReference, setEvidenceReference] = useState('');
  const [artifactSha256, setArtifactSha256] = useState('');
  const [issuedAt, setIssuedAt] = useState(() => new Date().toISOString().slice(0, 16));
  const [note, setNote] = useState('Pièce vérifiée et archivée dans la GED institutionnelle.');
  const [approvalNote, setApprovalNote] = useState('Validation après revue de la pièce et de son empreinte SHA-256.');
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    try {
      const next = await getHomologationDossiers();
      setDossiers(next);
      setSelectedReference(current => {
        if (current && next.some(item => item.reference === current)) return current;
        return next.find(item => ['draft', 'evidence_review', 'pending_approval', 'ready_for_decision'].includes(item.status))?.reference
          ?? next[0]?.reference
          ?? '';
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Dossiers d’homologation indisponibles.');
    }
  }

  useEffect(() => { void load(); }, []);

  const selected = useMemo(
    () => dossiers.find(item => item.reference === selectedReference) ?? null,
    [dossiers, selectedReference],
  );
  const selectedEvidenceCount = selected ? validEvidenceCount(selected.document) : 0;

  async function act(key: string, fn: () => Promise<unknown>, success: string) {
    setBusy(key); setMessage(null);
    try {
      await fn();
      setMessage(success);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Action d’homologation refusée.');
    } finally {
      setBusy(null);
    }
  }

  async function attachEvidence(event: FormEvent) {
    event.preventDefault();
    if (!canWrite || !selected) return;
    const reference = evidenceReference.trim();
    const digest = artifactSha256.trim().toLowerCase();
    if (!reference || reference.includes('://') || reference.includes('@')) {
      setMessage('La référence doit être un identifiant GED interne sans URL ni credential.');
      return;
    }
    if (!SHA256_RE.test(digest)) {
      setMessage('SHA-256 invalide : 64 caractères hexadécimaux sont obligatoires.');
      return;
    }
    const parsedIssuedAt = new Date(issuedAt);
    if (Number.isNaN(parsedIssuedAt.getTime())) {
      setMessage('Date de la pièce invalide.');
      return;
    }
    await act(
      `evidence-${selected.reference}-${code}`,
      () => attachHomologationEvidence(selected.reference, {
        code,
        reference,
        artifact_sha256: digest,
        issued_at: parsedIssuedAt.toISOString(),
        note: note.trim() || null,
      }),
      `${EVIDENCE_LABELS[code]} rattachée avec empreinte SHA-256.`,
    );
    setArtifactSha256('');
    setEvidenceReference('');
  }

  return (
    <div className="card" data-testid="homologation-evidence-workflow">
      <div className="card-header" style={{ alignItems: 'flex-start', gap: 12 }}>
        <div>
          <span className="card-title">Dossier de preuves — homologation DNTT</span>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
            5 pièces obligatoires · référence GED interne · SHA-256 · quatre yeux · décision finale
          </div>
        </div>
        {selected && <span className={`badge ${badge(selected.status)}`}>{selected.status}</span>}
      </div>

      {message && <div className="alert aw" style={{ marginBottom: 14 }}>{message}</div>}
      {dossiers.length === 0 && (
        <div style={{ color: 'var(--muted)' }}>Aucun dossier. Ouvrir d’abord un dossier depuis « Homologation nationale — DNTT ».</div>
      )}

      {dossiers.length > 0 && (
        <>
          <label style={{ display: 'block', marginBottom: 12 }}>
            Dossier actif
            <select value={selectedReference} onChange={event => setSelectedReference(event.target.value)}>
              {dossiers.map(item => (
                <option key={item.reference} value={item.reference}>
                  {item.reference} · {item.status} · {validEvidenceCount(item.document)}/5 hashées
                </option>
              ))}
            </select>
          </label>

          {selected && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 8, marginBottom: 14 }}>
                {EVIDENCE_CODES.map(evidenceCode => {
                  const evidence = selected.document.evidence?.[evidenceCode];
                  const hashed = hasValidHash(evidence);
                  return (
                    <div key={evidenceCode} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 11 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                        <strong style={{ fontSize: 12 }}>{EVIDENCE_LABELS[evidenceCode]}</strong>
                        <span className={`badge ${hashed ? 'bg' : 'br'}`}>
                          {hashed ? 'Hashée' : evidence ? 'À re-hasher' : 'Manquante'}
                        </span>
                      </div>
                      {evidence && (
                        <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 6 }}>
                          <div>{evidence.reference}</div>
                          {hashed && evidence.artifact_sha256 ? (
                            <code title={evidence.artifact_sha256}>{evidence.artifact_sha256.slice(0, 16)}…</code>
                          ) : (
                            <div>SHA-256 absent : remplacer cette ancienne référence avant soumission.</div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {canWrite && ['draft', 'evidence_review'].includes(selected.status) && (
                <form onSubmit={attachEvidence} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, display: 'grid', gap: 10, marginBottom: 14 }}>
                  <div style={{ fontWeight: 800 }}>Rattacher / remplacer une pièce</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10 }}>
                    <label>Type de preuve
                      <select value={code} onChange={event => setCode(event.target.value as HomologationEvidenceCode)}>
                        {EVIDENCE_CODES.map(item => <option key={item} value={item}>{EVIDENCE_LABELS[item]}</option>)}
                      </select>
                    </label>
                    <label>Référence GED interne
                      <input value={evidenceReference} onChange={event => setEvidenceReference(event.target.value)} placeholder="GED-DNTT-LEGAL-2026-001" />
                    </label>
                    <label>SHA-256 du document
                      <input value={artifactSha256} onChange={event => setArtifactSha256(event.target.value)} placeholder="64 caractères hexadécimaux" autoComplete="off" />
                    </label>
                    <label>Date d’émission
                      <input type="datetime-local" value={issuedAt} onChange={event => setIssuedAt(event.target.value)} />
                    </label>
                  </div>
                  <label>Note de revue
                    <textarea rows={2} value={note} onChange={event => setNote(event.target.value)} />
                  </label>
                  <button className="secondary-button" type="submit" disabled={busy !== null}>
                    {busy?.startsWith('evidence-') ? 'Enregistrement…' : 'Enregistrer la preuve hashée'}
                  </button>
                </form>
              )}

              {canWrite && (
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                  <label style={{ display: 'block', marginBottom: 8 }}>Note d’approbation / décision
                    <textarea rows={2} value={approvalNote} onChange={event => setApprovalNote(event.target.value)} />
                  </label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {['draft', 'evidence_review'].includes(selected.status) && (
                      <button
                        type="button"
                        className="btn-primary btn-sm"
                        disabled={busy !== null || selectedEvidenceCount !== 5}
                        onClick={() => void act(
                          `submit-${selected.reference}`,
                          () => submitHomologationDossier(selected.reference),
                          'Dossier soumis : intégrité des cinq pièces et readiness revalidées.',
                        )}
                      >
                        Soumettre les 5 preuves
                      </button>
                    )}
                    {['pending_approval', 'ready_for_decision'].includes(selected.status) && (selected.document.approvals?.length ?? 0) < 2 && (
                      <button
                        type="button"
                        className="secondary-button btn-sm"
                        disabled={busy !== null}
                        onClick={() => void act(
                          `approve-${selected.reference}`,
                          () => approveHomologationDossier(selected.reference, approvalNote.trim()),
                          'Approbation du dossier enregistrée.',
                        )}
                      >
                        Approuver ({selected.document.approvals?.length ?? 0}/2)
                      </button>
                    )}
                    {isSuperAdmin && selected.status === 'ready_for_decision' && (
                      <>
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          disabled={busy !== null}
                          onClick={() => void act(
                            `decide-${selected.reference}`,
                            () => decideHomologationDossier(selected.reference, true, approvalNote.trim()),
                            'Homologation enregistrée après revalidation des hashes, politique et readiness.',
                          )}
                        >
                          Homologuer
                        </button>
                        <button
                          type="button"
                          className="secondary-button btn-sm"
                          disabled={busy !== null}
                          onClick={() => void act(
                            `reject-${selected.reference}`,
                            () => decideHomologationDossier(selected.reference, false, approvalNote.trim()),
                            'Dossier rejeté avec traçabilité de la décision.',
                          )}
                        >
                          Rejeter
                        </button>
                      </>
                    )}
                  </div>
                  {selectedEvidenceCount !== 5 && ['draft', 'evidence_review'].includes(selected.status) && (
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 7 }}>
                      Soumission bloquée : {5 - selectedEvidenceCount} pièce(s) hashée(s) encore requise(s).
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
