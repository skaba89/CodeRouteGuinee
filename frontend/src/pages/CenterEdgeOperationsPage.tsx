import { useEffect, useMemo, useState } from 'react';
import { getOrCreateExamDeviceKey } from '../deviceIdentity';
import {
  activateEdgeLease,
  clearEdgeOperatorToken,
  getEdgeHealth,
  getEdgeOperatorStatus,
  getSavedEdgeUrl,
  getSessionOperatorToken,
  saveEdgeOperatorConnection,
  sendEdgeHeartbeat,
  syncEdgeAttempt,
  type EdgeActivation,
  type EdgeLeaseSummary,
  type EdgeOperatorStatus,
} from '../edgeOperatorClient';

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '0 Mo';
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} Ko`;
  return `${(value / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatTimestamp(value?: number | null): string {
  if (!value) return '—';
  return new Date(value * 1000).toLocaleString('fr-FR');
}

function formatDeadline(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('fr-FR');
}

function stateLabel(lease: EdgeLeaseSummary): { text: string; className: string } {
  if (lease.runtime_state === 'revalidation_required') return { text: 'Revalidation requise', className: 'br' };
  if (lease.status === 'synced') return { text: 'Synchronisé', className: 'bg' };
  if (lease.status === 'finalized') return { text: 'À synchroniser', className: 'bgo' };
  if (lease.status === 'active') return { text: 'En cours', className: 'bb' };
  return { text: lease.status, className: 'bgr' };
}

function MetricCard({ label, value, detail, tone = 'normal' }: { label: string; value: string | number; detail: string; tone?: 'normal' | 'good' | 'warn' | 'bad' }) {
  const border = tone === 'good' ? '#86efac' : tone === 'warn' ? '#fcd34d' : tone === 'bad' ? '#fca5a5' : 'var(--border)';
  return (
    <div className="card" style={{ padding: 16, borderColor: border }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.07em', fontWeight: 700 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 850, margin: '4px 0', color: 'var(--ink)' }}>{value}</div>
      <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>{detail}</div>
    </div>
  );
}

export default function CenterEdgeOperationsPage() {
  const browserStationKey = useMemo(() => getOrCreateExamDeviceKey(), []);
  const [edgeUrl, setEdgeUrl] = useState(() => getSavedEdgeUrl());
  const [operatorToken, setOperatorToken] = useState(() => getSessionOperatorToken());
  const [status, setStatus] = useState<EdgeOperatorStatus | null>(null);
  const [gatewayState, setGatewayState] = useState<'unknown' | 'online' | 'offline'>('unknown');
  const [wanState, setWanState] = useState<'unknown' | 'online' | 'offline'>('unknown');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [attemptId, setAttemptId] = useState('');
  const [stationKey, setStationKey] = useState(browserStationKey);
  const [activation, setActivation] = useState<EdgeActivation | null>(null);
  const [syncing, setSyncing] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState(false);
  const [filter, setFilter] = useState<'all' | 'active' | 'pending' | 'synced'>('all');

  const connected = Boolean(status && edgeUrl && operatorToken);

  const refresh = async (silent = false) => {
    if (!edgeUrl || !operatorToken) return;
    if (!silent) setBusy(true);
    setError('');
    try {
      await getEdgeHealth(edgeUrl);
      setGatewayState('online');
      const next = await getEdgeOperatorStatus(edgeUrl, operatorToken);
      setStatus(next);
      if (!silent) setMessage('Gateway Edge connecté et inventaire local actualisé.');
    } catch (err) {
      setGatewayState('offline');
      if (!silent) setError(err instanceof Error ? err.message : 'Gateway Edge inaccessible.');
    } finally {
      if (!silent) setBusy(false);
    }
  };

  const connect = async () => {
    setBusy(true); setError(''); setMessage('');
    try {
      const saved = saveEdgeOperatorConnection(edgeUrl, operatorToken);
      setEdgeUrl(saved.url);
      setOperatorToken(saved.token);
      await getEdgeHealth(saved.url);
      setGatewayState('online');
      const next = await getEdgeOperatorStatus(saved.url, saved.token);
      setStatus(next);
      setMessage('Connexion locale sécurisée établie.');
    } catch (err) {
      setGatewayState('offline');
      setStatus(null);
      setError(err instanceof Error ? err.message : 'Connexion au gateway impossible.');
    } finally { setBusy(false); }
  };

  const heartbeat = async () => {
    if (!edgeUrl || !operatorToken) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await sendEdgeHeartbeat(edgeUrl, operatorToken);
      setWanState('online');
      setGatewayState('online');
      setMessage('Liaison DNTT centrale confirmée par heartbeat signé.');
      await refresh(true);
    } catch (err) {
      setWanState('offline');
      setGatewayState('online');
      setError(err instanceof Error ? err.message : 'La liaison DNTT est indisponible.');
    } finally { setBusy(false); }
  };

  const activate = async () => {
    if (!attemptId.trim() || !stationKey.trim() || !edgeUrl || !operatorToken) return;
    setBusy(true); setError(''); setMessage(''); setActivation(null); setCopied(false);
    try {
      const result = await activateEdgeLease(edgeUrl, operatorToken, attemptId, stationKey);
      setActivation(result);
      setWanState('online');
      setMessage(`Paquet Edge prêt : ${result.question_count} questions et médias préchargés.`);
      await refresh(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation Edge impossible.');
    } finally { setBusy(false); }
  };

  const syncOne = async (lease: EdgeLeaseSummary) => {
    if (!edgeUrl || !operatorToken) return;
    setSyncing(current => ({ ...current, [lease.attempt_id]: true }));
    setError(''); setMessage('');
    try {
      await syncEdgeAttempt(edgeUrl, operatorToken, lease.attempt_id);
      setWanState('online');
      setMessage(`Tentative ${lease.attempt_id.slice(0, 8)}… synchronisée avec la DNTT.`);
      await refresh(true);
    } catch (err) {
      setWanState('offline');
      setError(err instanceof Error ? err.message : 'Synchronisation impossible.');
    } finally {
      setSyncing(current => ({ ...current, [lease.attempt_id]: false }));
    }
  };

  const syncAll = async () => {
    if (!status) return;
    const pending = status.leases.filter(item => item.sync_pending);
    for (const lease of pending) await syncOne(lease);
  };

  const copyCandidateLink = async () => {
    if (!activation?.candidate_url) return;
    try {
      await navigator.clipboard.writeText(activation.candidate_url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setError('Copie automatique impossible. Sélectionnez le lien manuellement.');
    }
  };

  const disconnect = () => {
    clearEdgeOperatorToken();
    setOperatorToken('');
    setStatus(null);
    setWanState('unknown');
    setGatewayState('unknown');
    setActivation(null);
    setMessage('Session opérateur Edge fermée.');
  };

  useEffect(() => {
    if (!edgeUrl || !operatorToken) return;
    void refresh(true);
    const timer = window.setInterval(() => { void refresh(true); }, 10_000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edgeUrl, operatorToken]);

  useEffect(() => {
    if (!activation?.claim_expires_at) return;
    const delay = Math.max(0, activation.claim_expires_at * 1000 - Date.now());
    const timer = window.setTimeout(() => setActivation(null), Math.min(delay + 1000, 2_147_000_000));
    return () => window.clearTimeout(timer);
  }, [activation]);

  const filteredLeases = (status?.leases ?? []).filter(lease => {
    if (filter === 'all') return true;
    if (filter === 'active') return lease.status === 'active';
    if (filter === 'pending') return lease.sync_pending || lease.runtime_state === 'revalidation_required';
    return lease.status === 'synced';
  });

  return (
    <main className="screen" role="main" aria-label="Console Center Edge" style={{ maxWidth: 1180, margin: '0 auto' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div>
          <span className="eyebrow">Mode résilient centre</span>
          <h1>Console Center Edge</h1>
          <p>Pilotez le gateway local, les examens hors ligne et la synchronisation DNTT sans exposer la banque ni le score.</p>
        </div>
        <a href="#/center" className="secondary-button btn-sm" style={{ textDecoration: 'none' }}>← Retour espace centre</a>
      </div>

      <div className="alert aw" style={{ marginBottom: 16 }}>
        Le secret opérateur reste uniquement dans cet onglet. Le verdict candidat n'est jamais calculé sur le gateway : la DNTT centrale reste la source de vérité.
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">Connexion au gateway local</span>
          {connected && <span className="badge bg">Session opérateur active</span>}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 1fr) minmax(260px, 1fr) auto', gap: 12, alignItems: 'end' }}>
          <label>URL HTTPS du gateway
            <input value={edgeUrl} onChange={event => setEdgeUrl(event.target.value)} placeholder="https://edge-ratoma.coderoute.local:8443" autoComplete="off" />
          </label>
          <label>Secret opérateur
            <input type="password" value={operatorToken} onChange={event => setOperatorToken(event.target.value)} placeholder="Secret local 32+ caractères" autoComplete="off" />
          </label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn-success" disabled={busy || !edgeUrl || operatorToken.length < 32} onClick={() => void connect()}>
              {busy ? 'Connexion…' : 'Connecter'}
            </button>
            {connected && <button type="button" className="secondary-button" onClick={disconnect}>Fermer</button>}
          </div>
        </div>
        <p style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 10 }}>Poste navigateur courant : <code>{browserStationKey}</code></p>
      </div>

      {(message || error) && (
        <div className={`alert ${error ? 'ar' : 'as'}`} style={{ marginBottom: 16 }} role="status">
          {error || message}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 10, marginBottom: 16 }}>
        <MetricCard label="Gateway local" value={gatewayState === 'online' ? 'EN LIGNE' : gatewayState === 'offline' ? 'HORS LIGNE' : '—'} detail={status?.software_version ?? 'Connexion non vérifiée'} tone={gatewayState === 'online' ? 'good' : gatewayState === 'offline' ? 'bad' : 'normal'} />
        <MetricCard label="Liaison DNTT" value={wanState === 'online' ? 'OK' : wanState === 'offline' ? 'COUPÉE' : 'À TESTER'} detail="Heartbeat Ed25519" tone={wanState === 'online' ? 'good' : wanState === 'offline' ? 'warn' : 'normal'} />
        <MetricCard label="Examens locaux" value={status?.leases.length ?? 0} detail={`${status?.lease_counts?.active ?? 0} en cours`} />
        <MetricCard label="À synchroniser" value={status?.sync_pending ?? 0} detail="Journaux finalisés" tone={(status?.sync_pending ?? 0) > 0 ? 'warn' : 'good'} />
        <MetricCard label="Revalidation" value={status?.revalidation_required ?? 0} detail="Après reboot gateway" tone={(status?.revalidation_required ?? 0) > 0 ? 'bad' : 'good'} />
        <MetricCard label="Cache médias" value={status ? formatBytes(status.media_cache.bytes) : '—'} detail={`${status?.media_cache.files ?? 0} fichiers vérifiés`} />
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <button type="button" className="btn-primary" disabled={!connected || busy} onClick={() => void heartbeat()}>Tester la liaison DNTT</button>
        <button type="button" className="secondary-button" disabled={!connected || busy} onClick={() => void refresh()}>Actualiser</button>
        <button type="button" className="btn-success" disabled={!connected || !status?.sync_pending || busy} onClick={() => void syncAll()}>Synchroniser tout ({status?.sync_pending ?? 0})</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header"><span className="card-title">Préparer une tentative en mode Edge</span></div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
          La tentative doit déjà avoir été ouverte par le parcours officiel et liée à un poste CenterStation actif. Le gateway précharge les 40 questions de cette tentative et ses médias, sans clé de correction.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px,1fr) minmax(240px,1fr) auto', gap: 12, alignItems: 'end' }}>
          <label>ID de tentative officielle
            <input value={attemptId} onChange={event => setAttemptId(event.target.value)} placeholder="UUID de la tentative" autoComplete="off" />
          </label>
          <label>Poste candidat cible
            <input value={stationKey} onChange={event => setStationKey(event.target.value)} placeholder="CRG-STATION-..." autoComplete="off" />
          </label>
          <button type="button" className="btn-success" disabled={!connected || busy || !attemptId.trim() || stationKey.trim().length < 4} onClick={() => void activate()}>
            Précharger et activer
          </button>
        </div>

        {activation && (
          <div style={{ marginTop: 16, padding: 14, border: '1px solid #86efac', background: '#E6F3EC', borderRadius: 10 }}>
            <div style={{ fontWeight: 800, color: '#006B3F', marginBottom: 6 }}>Paquet Edge prêt pour le poste</div>
            <div style={{ fontSize: 12, color: 'var(--ink2)', marginBottom: 10 }}>
              {activation.question_count} questions · claim valable jusqu'au {formatTimestamp(activation.claim_expires_at)}
            </div>
            <input readOnly value={activation.candidate_url} onFocus={event => event.currentTarget.select()} style={{ width: '100%', fontSize: 11.5, marginBottom: 8 }} />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button type="button" className="btn-success btn-sm" onClick={() => void copyCandidateLink()}>{copied ? 'Lien copié ✓' : 'Copier le lien candidat'}</button>
              {stationKey === browserStationKey && (
                <button type="button" className="secondary-button btn-sm" onClick={() => { window.location.href = activation.candidate_url; }}>Ouvrir sur ce poste</button>
              )}
              <button type="button" className="secondary-button btn-sm" onClick={() => setActivation(null)}>Masquer le lien</button>
            </div>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>Ce lien contient un claim temporaire. Ne l'envoyez qu'au poste candidat correspondant.</p>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header" style={{ gap: 12, flexWrap: 'wrap' }}>
          <span className="card-title">Tentatives présentes sur le gateway</span>
          <div style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>
            {(['all','active','pending','synced'] as const).map(value => (
              <button key={value} type="button" className={filter === value ? 'btn-success btn-sm' : 'secondary-button btn-sm'} onClick={() => setFilter(value)}>
                {value === 'all' ? 'Toutes' : value === 'active' ? 'En cours' : value === 'pending' ? 'À traiter' : 'Synchronisées'}
              </button>
            ))}
          </div>
        </div>
        {!connected ? (
          <div className="empty-state"><p>Connectez d'abord le gateway local.</p></div>
        ) : filteredLeases.length === 0 ? (
          <div className="empty-state"><p>Aucune tentative dans ce filtre.</p></div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Tentative</th><th>Poste</th><th>État</th><th>Réponses</th><th>Claim</th><th>Deadline</th><th>Action</th></tr></thead>
              <tbody>
                {filteredLeases.map(lease => {
                  const state = stateLabel(lease);
                  return (
                    <tr key={lease.attempt_id}>
                      <td><code style={{ fontSize: 10.5 }}>{lease.attempt_id.slice(0, 12)}…</code></td>
                      <td>
                        <div style={{ fontWeight: 650 }}>{lease.station.label || lease.station.device_key || '—'}</div>
                        {lease.station.room && <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{lease.station.room}</div>}
                      </td>
                      <td><span className={`badge ${state.className}`}>{state.text}</span></td>
                      <td>{lease.event_count} événements</td>
                      <td>{lease.claim_state === 'claimed' ? 'Consommé' : lease.claim_state === 'pending' ? 'Disponible' : lease.claim_state === 'expired' ? 'Expiré' : '—'}</td>
                      <td style={{ fontSize: 11 }}>{formatDeadline(lease.deadline_at)}</td>
                      <td>
                        {lease.sync_pending ? (
                          <button type="button" className="btn-success btn-sm" disabled={Boolean(syncing[lease.attempt_id])} onClick={() => void syncOne(lease)}>
                            {syncing[lease.attempt_id] ? 'Sync…' : 'Synchroniser'}
                          </button>
                        ) : lease.runtime_state === 'revalidation_required' ? (
                          <span style={{ fontSize: 11, color: 'var(--red)' }}>Retour WAN requis</span>
                        ) : (
                          <span style={{ fontSize: 11, color: 'var(--muted)' }}>—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
