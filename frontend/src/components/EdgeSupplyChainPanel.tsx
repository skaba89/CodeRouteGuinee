import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { canUseProtectedActions, useAuthSession } from '../authSession';
import {
  attachEdgeSupplyChainEvidence,
  getEdgeReleases,
  type EdgeRelease,
  type EdgeSupplyChainEvidence,
} from '../edgeReleaseClient';

function evidenceReady(release: EdgeRelease): boolean {
  const evidence = release.manifest.supply_chain;
  return Boolean(
    evidence
    && evidence.vulnerability_scan_status === 'passed'
    && evidence.subject_sha256 === release.manifest.artifact.sha256,
  );
}

function parseEvidence(text: string): EdgeSupplyChainEvidence {
  const parsed = JSON.parse(text) as Partial<EdgeSupplyChainEvidence>;
  const required = [
    'builder', 'source_commit_sha', 'workflow_ref', 'provenance_url',
    'sbom_sha256', 'subject_sha256', 'vulnerability_scan_status',
  ] as const;
  for (const key of required) {
    if (!String(parsed[key] ?? '').trim()) throw new Error(`Preuve CI incomplète : ${key} manquant.`);
  }
  if (parsed.vulnerability_scan_status !== 'passed' && parsed.vulnerability_scan_status !== 'failed') {
    throw new Error('vulnerability_scan_status doit valoir passed ou failed.');
  }
  return parsed as EdgeSupplyChainEvidence;
}

export function EdgeSupplyChainPanel() {
  const { currentUser } = useAuthSession();
  const canManage = canUseProtectedActions(currentUser, false, ['super_admin']);
  const [releases, setReleases] = useState<EdgeRelease[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [evidenceText, setEvidenceText] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function load() {
    try {
      const data = await getEdgeReleases();
      setReleases(data);
      if (!selectedId) {
        const candidate = data.find(item => ['draft', 'paused'].includes(item.status) && !evidenceReady(item));
        if (candidate) setSelectedId(candidate.release_id);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Releases Edge indisponibles.');
    }
  }

  useEffect(() => { void load(); }, []);

  const selected = useMemo(() => releases.find(item => item.release_id === selectedId) ?? null, [releases, selectedId]);

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      parseEvidence(text);
      setEvidenceText(text);
      setMessage(`Preuve CI chargée : ${file.name}`);
    } catch (error) {
      setEvidenceText('');
      setMessage(error instanceof Error ? error.message : 'Fichier de preuve illisible.');
    } finally {
      event.target.value = '';
    }
  }

  async function attachEvidence() {
    if (!canManage || !selected) return;
    setBusy(true); setMessage('');
    try {
      const evidence = parseEvidence(evidenceText);
      if (evidence.subject_sha256 !== selected.manifest.artifact.sha256) {
        throw new Error('Le digest du bundle CI ne correspond pas à l’artefact du draft sélectionné.');
      }
      const updated = await attachEdgeSupplyChainEvidence(selected.release_id, evidence);
      setMessage(
        updated.manifest.supply_chain?.vulnerability_scan_status === 'passed'
          ? 'Preuve CI rattachée et manifeste re-signé. Le canary peut maintenant passer au garde opérationnel.'
          : 'Preuve rattachée, mais le scan est en échec : rollout toujours bloqué.',
      );
      setEvidenceText('');
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Rattachement de preuve impossible.');
    } finally { setBusy(false); }
  }

  return (
    <div className="card" data-testid="edge-supply-chain-panel" style={{ marginTop: 20 }}>
      <div className="card-header" style={{ alignItems: 'flex-start' }}>
        <div>
          <span className="card-title">Supply chain Edge — preuve avant canary</span>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
            Import du control-plane-evidence.json généré par la CI attestée
          </div>
        </div>
        <span className={`badge ${canManage ? 'bg' : 'bgr'}`}>{canManage ? 'Super-admin' : 'Lecture seule'}</span>
      </div>

      {message && <div className="alert aw" style={{ marginBottom: 14 }}>{message}</div>}

      <div style={{ display: 'grid', gap: 10 }}>
        {releases.map(release => {
          const evidence = release.manifest.supply_chain;
          const ready = evidenceReady(release);
          return (
            <div key={release.release_id} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <strong>{release.manifest.software_version}</strong>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                    {release.status} · SHA {release.manifest.artifact.sha256.slice(0, 16)}…
                  </div>
                </div>
                <span className={`badge ${ready ? 'bg' : evidence ? 'br' : 'bgo'}`}>
                  {ready ? 'Preuve CI valide' : evidence ? 'Scan en échec' : 'Preuve manquante'}
                </span>
              </div>
              {evidence && (
                <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 8 }}>
                  Commit {evidence.source_commit_sha.slice(0, 12)}… · SBOM {evidence.sbom_sha256.slice(0, 12)}… · {evidence.builder}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {canManage && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          <div className="g2">
            <label>Draft / release en pause
              <select value={selectedId} onChange={event => setSelectedId(event.target.value)}>
                <option value="">Sélectionner…</option>
                {releases.filter(item => ['draft', 'paused'].includes(item.status)).map(item => (
                  <option key={item.release_id} value={item.release_id}>{item.manifest.software_version} · {item.status}</option>
                ))}
              </select>
            </label>
            <label>Bundle de preuve CI
              <input type="file" accept="application/json,.json" onChange={event => void importFile(event)} />
            </label>
          </div>
          <textarea
            value={evidenceText}
            onChange={event => setEvidenceText(event.target.value)}
            rows={8}
            placeholder='{"builder":"github-actions", ...}'
            style={{ width: '100%', marginTop: 10, fontFamily: 'monospace', fontSize: 11.5 }}
          />
          <div className="actions" style={{ marginTop: 10 }}>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={busy || !selected || !evidenceText.trim()}
              onClick={() => void attachEvidence()}
            >
              {busy ? 'Vérification / signature…' : 'Rattacher la preuve et re-signer'}
            </button>
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 8 }}>
            Le backend recalcule les invariants : le digest sujet doit égaler l’artefact, le scan doit être « passed » pour autoriser le rollout, et les URLs de provenance doivent être HTTPS publiques.
          </p>
        </div>
      )}
    </div>
  );
}
