import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { canUseProtectedActions, useAuthSession } from '../authSession';
import { getNationalEdgeFleet, type EdgeFleetNode } from '../edgeFleetClient';
import {
  createEdgeRelease,
  getEdgeReleaseRollout,
  getEdgeReleases,
  updateEdgeReleaseRollout,
  type EdgeRelease,
  type EdgeReleaseRollout,
} from '../edgeReleaseClient';

function fmtBytes(value: number): string {
  if (value < 1024) return `${value} o`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} Ko`;
  return `${(value / (1024 * 1024)).toFixed(1)} Mo`;
}

function rolloutBadge(value: string): string {
  if (value === 'released') return 'bg';
  if (value === 'canary' || value === 'rolling') return 'bgo';
  if (value === 'rollback' || value === 'revoked') return 'br';
  return 'bgr';
}

export function EdgeReleasePanel() {
  const { currentUser } = useAuthSession();
  const canManage = canUseProtectedActions(currentUser, false, ['super_admin']);
  const [releases, setReleases] = useState<EdgeRelease[]>([]);
  const [nodes, setNodes] = useState<EdgeFleetNode[]>([]);
  const [selectedCanaries, setSelectedCanaries] = useState<string[]>([]);
  const [rolloutDetails, setRolloutDetails] = useState<Record<string, EdgeReleaseRollout>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [version, setVersion] = useState('edge-agent-0.3.1');
  const [artifactUrl, setArtifactUrl] = useState('');
  const [artifactSha, setArtifactSha] = useState('');
  const [artifactSize, setArtifactSize] = useState('');
  const [minimum, setMinimum] = useState('edge-agent-0.3.0');
  const [notes, setNotes] = useState('');
  const [rollbackReleaseId, setRollbackReleaseId] = useState('');

  const canaryCandidates = useMemo(
    () => nodes.filter(node => node.status === 'active' && node.online && node.health_status !== 'critical'),
    [nodes],
  );

  async function load() {
    setLoading(true);
    try {
      const [releaseData, fleet] = await Promise.all([getEdgeReleases(), getNationalEdgeFleet()]);
      setReleases(releaseData);
      setNodes(fleet.nodes);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Chargement des releases Edge impossible.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function toggleCanary(nodeId: string) {
    setSelectedCanaries(current => current.includes(nodeId)
      ? current.filter(value => value !== nodeId)
      : [...current, nodeId]);
  }

  async function createRelease(event: FormEvent) {
    event.preventDefault();
    if (!canManage) return;
    setBusy('create'); setMessage(null);
    try {
      await createEdgeRelease({
        software_version: version.trim(),
        artifact_url: artifactUrl.trim(),
        artifact_sha256: artifactSha.trim().toLowerCase(),
        artifact_size_bytes: Number(artifactSize),
        min_current_version: minimum.trim() || undefined,
        release_notes: notes.trim() || undefined,
        canary_node_ids: selectedCanaries,
        rollback_release_id: rollbackReleaseId || undefined,
      });
      setMessage('Manifeste signé créé en draft. Aucun gateway ne peut encore le recevoir.');
      setArtifactUrl(''); setArtifactSha(''); setArtifactSize(''); setNotes('');
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Création de release impossible.');
    } finally { setBusy(null); }
  }

  async function changeRollout(release: EdgeRelease, rolloutStatus: string, percent: number) {
    if (!canManage) return;
    const destructive = rolloutStatus === 'revoked' || rolloutStatus === 'rollback';
    if (destructive && !window.confirm(
      rolloutStatus === 'rollback'
        ? `Déclencher le rollback national de ${release.manifest.software_version} ?`
        : `Révoquer définitivement ${release.manifest.software_version} ?`,
    )) return;
    setBusy(`${release.release_id}:${rolloutStatus}`); setMessage(null);
    try {
      await updateEdgeReleaseRollout(release.release_id, {
        rollout_status: rolloutStatus,
        rollout_percent: percent,
        canary_node_ids: release.canary_node_ids,
        allowed_center_ids: release.allowed_center_ids,
        rollback_release_id: release.rollback_release_id || undefined,
        reason: rolloutStatus === 'canary'
          ? 'Démarrage canary DNTT depuis la console nationale'
          : rolloutStatus === 'rollback'
            ? 'Rollback ordonné par la DNTT depuis la console nationale'
            : `Transition DNTT vers ${rolloutStatus}${percent ? ` (${percent}%)` : ''}`,
      });
      setMessage(`Release ${release.manifest.software_version} → ${rolloutStatus}${percent ? ` ${percent}%` : ''}.`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Mise à jour du rollout impossible.');
    } finally { setBusy(null); }
  }

  async function loadDetails(releaseId: string) {
    setBusy(`${releaseId}:details`); setMessage(null);
    try {
      const detail = await getEdgeReleaseRollout(releaseId);
      setRolloutDetails(current => ({ ...current, [releaseId]: detail }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Détails de rollout indisponibles.');
    } finally { setBusy(null); }
  }

  if (loading) return <div className="card"><p style={{ padding: 16, color: 'var(--muted)' }}>Chargement des releases Center Edge…</p></div>;

  return (
    <div className="card" data-testid="edge-release-panel" style={{ marginTop: 20 }}>
      <div className="card-header" style={{ alignItems: 'flex-start' }}>
        <div>
          <span className="card-title">Releases Center Edge — déploiement sécurisé</span>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
            Manifestes signés · canary · vagues progressives · attestations · rollback
          </div>
        </div>
        <span className={`badge ${canManage ? 'bg' : 'bgr'}`}>{canManage ? 'Pilotage super-admin' : 'Lecture seule'}</span>
      </div>

      {message && <div className="alert aw" style={{ marginBottom: 14 }}>{message}</div>}

      {canManage && (
        <form onSubmit={createRelease} className="card" style={{ padding: 16, marginBottom: 16, background: 'var(--bg)' }}>
          <div style={{ fontWeight: 800, marginBottom: 12 }}>Nouveau manifeste signé</div>
          <div className="g2">
            <label>Version cible<input value={version} onChange={event => setVersion(event.target.value)} required /></label>
            <label>Version minimale actuelle<input value={minimum} onChange={event => setMinimum(event.target.value)} /></label>
            <label style={{ gridColumn: '1 / -1' }}>URL HTTPS de l'artefact<input value={artifactUrl} onChange={event => setArtifactUrl(event.target.value)} placeholder="https://releases.coderoute.gov.gn/edge-agent-0.3.1.tar.gz" required /></label>
            <label>SHA-256<input value={artifactSha} onChange={event => setArtifactSha(event.target.value)} minLength={64} maxLength={64} required /></label>
            <label>Taille exacte (octets)<input type="number" min="1" value={artifactSize} onChange={event => setArtifactSize(event.target.value)} required /></label>
            <label style={{ gridColumn: '1 / -1' }}>Notes de release<textarea value={notes} onChange={event => setNotes(event.target.value)} rows={3} /></label>
            <label>Rollback vers
              <select value={rollbackReleaseId} onChange={event => setRollbackReleaseId(event.target.value)}>
                <option value="">Aucune / première release</option>
                {releases.map(item => <option key={item.release_id} value={item.release_id}>{item.manifest.software_version}</option>)}
              </select>
            </label>
          </div>

          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 800, marginBottom: 7 }}>Gateways canary autorisés</div>
            {canaryCandidates.length === 0
              ? <div style={{ color: 'var(--muted)', fontSize: 12 }}>Aucun gateway sain et en ligne disponible.</div>
              : <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {canaryCandidates.map(node => (
                    <label key={node.node_id} style={{ display: 'flex', alignItems: 'center', gap: 6, border: '1px solid var(--border)', borderRadius: 8, padding: '7px 9px', fontSize: 12 }}>
                      <input type="checkbox" checked={selectedCanaries.includes(node.node_id)} onChange={() => toggleCanary(node.node_id)} />
                      {node.label || node.reference} · {node.center_code}
                    </label>
                  ))}
                </div>}
          </div>

          <div className="actions" style={{ marginTop: 14 }}>
            <button className="btn-primary btn-sm" disabled={busy === 'create' || artifactSha.length !== 64 || !artifactUrl || Number(artifactSize) <= 0}>
              {busy === 'create' ? 'Signature…' : 'Créer en draft signé'}
            </button>
          </div>
        </form>
      )}

      <div style={{ display: 'grid', gap: 12 }}>
        {releases.length === 0 && <div style={{ padding: 18, color: 'var(--muted)' }}>Aucune release Edge enregistrée.</div>}
        {releases.map(release => {
          const detail = rolloutDetails[release.release_id];
          const counts = detail?.attestation_counts;
          return (
            <div key={release.release_id} className="card" style={{ padding: 15 }} data-testid={`edge-release-${release.release_id}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 850 }}>{release.manifest.software_version}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>{release.reference} · {fmtBytes(release.manifest.artifact.size_bytes)}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3, fontFamily: 'monospace' }}>SHA {release.manifest.artifact.sha256.slice(0, 16)}…</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className={`badge ${rolloutBadge(release.rollout_status)}`}>{release.rollout_status}</span>
                  <div style={{ fontSize: 12, fontWeight: 800, marginTop: 6 }}>{release.rollout_percent}%</div>
                </div>
              </div>

              {release.manifest.release_notes && <p style={{ fontSize: 12, color: 'var(--muted)', margin: '10px 0 0' }}>{release.manifest.release_notes}</p>}

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                <button className="secondary-button btn-sm" type="button" onClick={() => void loadDetails(release.release_id)}>
                  Détails / attestations
                </button>
                {canManage && <>
                  <button className="secondary-button btn-sm" type="button" disabled={release.canary_node_ids.length === 0 || busy !== null} onClick={() => void changeRollout(release, 'canary', 0)}>Canary</button>
                  {[10, 25, 50].map(percent => <button key={percent} className="secondary-button btn-sm" type="button" disabled={busy !== null} onClick={() => void changeRollout(release, 'rolling', percent)}>{percent}%</button>)}
                  <button className="btn-primary btn-sm" type="button" disabled={busy !== null} onClick={() => void changeRollout(release, 'released', 100)}>100% national</button>
                  <button className="secondary-button btn-sm" type="button" disabled={busy !== null} onClick={() => void changeRollout(release, 'paused', 0)}>Pause</button>
                  {release.rollback_release_id && <button className="secondary-button btn-sm" type="button" disabled={busy !== null} onClick={() => void changeRollout(release, 'rollback', 100)}>Rollback</button>}
                  <button className="secondary-button btn-sm" type="button" disabled={busy !== null || release.rollout_status === 'revoked'} onClick={() => void changeRollout(release, 'revoked', 0)}>Révoquer</button>
                </>}
              </div>

              {detail && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 12 }}>
                    <strong>Éligibles : {detail.eligible_nodes}</strong>
                    <span>Staged : {counts.staged}</span>
                    <span>Installés : {counts.installed}</span>
                    <span style={{ color: counts.failed ? 'var(--red)' : undefined }}>Échecs : {counts.failed}</span>
                    <span>Rollbacks : {counts.rolled_back}</span>
                  </div>
                  {detail.attestations.length > 0 && (
                    <div className="table-wrap" style={{ marginTop: 10 }}>
                      <table>
                        <thead><tr><th>Gateway</th><th>Centre</th><th>Résultat</th><th>Version</th><th>Attestation</th></tr></thead>
                        <tbody>{detail.attestations.map(item => (
                          <tr key={item.attestation_id}>
                            <td>{item.node_id || '—'}</td><td>{item.center_id || '—'}</td>
                            <td><span className={`badge ${item.result === 'failed' ? 'br' : 'bg'}`}>{item.result}</span></td>
                            <td>{item.software_version || '—'}</td>
                            <td>{item.attested_at ? new Date(item.attested_at).toLocaleString('fr-FR') : '—'}</td>
                          </tr>
                        ))}</tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
