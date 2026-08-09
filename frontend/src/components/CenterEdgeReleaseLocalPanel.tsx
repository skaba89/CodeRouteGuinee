import { useEffect, useState } from 'react';
import {
  attestLocalEdgeInstall,
  checkLocalEdgeRelease,
  getLocalEdgeReleaseStatus,
  getSavedEdgeUrl,
  getSessionOperatorToken,
  stageLocalEdgeRelease,
  type EdgeLocalReleaseState,
  type EdgeReleaseOffer,
} from '../edgeOperatorClient';

function connection(): { url: string; token: string } | null {
  const url = getSavedEdgeUrl();
  const token = getSessionOperatorToken();
  return url && token ? { url, token } : null;
}

export function CenterEdgeReleaseLocalPanel() {
  const [status, setStatus] = useState<EdgeLocalReleaseState | null>(null);
  const [offer, setOffer] = useState<EdgeReleaseOffer | null>(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function refresh(silent = false) {
    const current = connection();
    if (!current) {
      if (!silent) setError('Connectez d’abord la session opérateur dans la console ci-dessus.');
      return;
    }
    if (!silent) setBusy('status');
    try {
      setStatus(await getLocalEdgeReleaseStatus(current.url, current.token));
      if (!silent) setError('');
    } catch (err) {
      if (!silent) setError(err instanceof Error ? err.message : 'État release local indisponible.');
    } finally { if (!silent) setBusy(''); }
  }

  async function check() {
    const current = connection();
    if (!current) { setError('Connectez d’abord la session opérateur.'); return; }
    setBusy('check'); setError(''); setMessage('');
    try {
      const next = await checkLocalEdgeRelease(current.url, current.token);
      setOffer(next);
      setMessage(next.update_available
        ? `${next.action === 'rollback' ? 'Rollback' : 'Mise à jour'} disponible : ${next.release?.manifest.software_version ?? 'version signée'}.`
        : 'Aucune mise à jour autorisée pour ce gateway dans la vague actuelle.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Vérification de release impossible.');
    } finally { setBusy(''); }
  }

  async function stage() {
    const current = connection();
    if (!current) { setError('Connectez d’abord la session opérateur.'); return; }
    setBusy('stage'); setError(''); setMessage('');
    try {
      const result = await stageLocalEdgeRelease(current.url, current.token);
      setMessage(result.staged
        ? `Release ${result.software_version ?? ''} téléchargée et vérifiée. L’updater local peut maintenant l’appliquer.`
        : 'Aucune release à précharger.');
      await refresh(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Préchargement de release impossible.');
    } finally { setBusy(''); }
  }

  async function attest() {
    const current = connection();
    if (!current) { setError('Connectez d’abord la session opérateur.'); return; }
    setBusy('attest'); setError(''); setMessage('');
    try {
      await attestLocalEdgeInstall(current.url, current.token);
      setMessage('Reçu d’installation/rollback attesté auprès de la DNTT.');
      await refresh(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Attestation de l’installation impossible.');
    } finally { setBusy(''); }
  }

  useEffect(() => { void refresh(true); }, []);

  const staged = status?.staged;
  const receipt = status?.install_receipt;

  return (
    <section style={{ maxWidth: 1180, margin: '0 auto 40px', padding: '0 20px' }} data-testid="center-edge-release-local">
      <div className="card">
        <div className="card-header" style={{ alignItems: 'flex-start' }}>
          <div>
            <span className="card-title">Maintenance logicielle du gateway</span>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
              Releases signées DNTT · staging non privilégié · installation locale séparée
            </div>
          </div>
          <span className={`badge ${status?.enabled ? 'bg' : 'bgr'}`}>{status?.enabled ? 'P8 actif' : 'À connecter'}</span>
        </div>

        <div className="alert aw" style={{ marginBottom: 14 }}>
          Cette interface ne peut pas installer du code ni exécuter de commande système. Elle vérifie et précharge uniquement l’artefact signé.
        </div>
        {error && <div className="alert ar" style={{ marginBottom: 12 }}>{error}</div>}
        {message && <div className="alert as" style={{ marginBottom: 12 }}>{message}</div>}

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          <button type="button" className="btn-primary btn-sm" disabled={Boolean(busy)} onClick={() => void check()}>
            {busy === 'check' ? 'Vérification…' : 'Vérifier une mise à jour'}
          </button>
          <button type="button" className="btn-success btn-sm" disabled={Boolean(busy) || offer?.update_available !== true} onClick={() => void stage()}>
            {busy === 'stage' ? 'Téléchargement…' : 'Précharger et vérifier'}
          </button>
          <button type="button" className="secondary-button btn-sm" disabled={Boolean(busy)} onClick={() => void refresh()}>
            État local
          </button>
          <button type="button" className="secondary-button btn-sm" disabled={Boolean(busy) || !receipt} onClick={() => void attest()}>
            Attester le reçu d’installation
          </button>
        </div>

        {offer?.update_available && offer.release && (
          <div style={{ padding: 12, border: '1px solid var(--border)', borderRadius: 10, marginBottom: 12 }}>
            <strong>{offer.action === 'rollback' ? 'Rollback autorisé' : 'Release autorisée'} : {offer.release.manifest.software_version}</strong>
            <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
              SHA {offer.release.manifest.artifact.sha256.slice(0, 16)}… · {(offer.release.manifest.artifact.size_bytes / (1024 * 1024)).toFixed(1)} Mo
            </div>
            {offer.release.manifest.release_notes && <p style={{ fontSize: 12, marginBottom: 0 }}>{offer.release.manifest.release_notes}</p>}
          </div>
        )}

        {staged && !staged.corrupt && (
          <div style={{ padding: 12, border: '1px solid #86efac', borderRadius: 10, marginBottom: 12 }}>
            <strong>Artefact vérifié : {staged.software_version}</strong>
            <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
              Action : {staged.action || 'install'} · SHA {staged.artifact_sha256?.slice(0, 16)}…
            </div>
            <p style={{ fontSize: 12, margin: '10px 0 4px' }}>Sur le gateway, l’administrateur système exécute :</p>
            <code style={{ display: 'block', overflowX: 'auto', padding: 10, borderRadius: 8, background: 'var(--bg)' }}>
              PYTHONPATH=edge_agent python edge_agent/scripts/apply_verified_release.py --release-root /opt/coderoute-edge/releases
            </code>
          </div>
        )}
        {staged?.corrupt && <div className="alert ar">État de staging local corrompu : intervention technique requise.</div>}

        {receipt && !receipt.corrupt && (
          <div style={{ fontSize: 12 }}>
            Reçu local en attente d’attestation : <strong>{receipt.result}</strong> · {receipt.software_version}
          </div>
        )}
      </div>
    </section>
  );
}
