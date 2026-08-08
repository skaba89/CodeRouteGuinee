import { useEffect, useState } from 'react';
import { getExamResults, type ExamDetailedResult } from '../api';
import { clearEdgeSession } from '../edgeExamSession';
import { clearPendingEdgeResult, getPendingEdgeResultAttempt } from '../edgeExamFetchBridge';

const ACTIVE_ATTEMPT_KEY = 'coderoute:official-exam:active-attempt';

export default function EdgePendingPage() {
  const [attemptId] = useState(() => getPendingEdgeResultAttempt());
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<ExamDetailedResult | null>(null);

  const checkCentralResult = async () => {
    if (!attemptId) return;
    setChecking(true);
    setMessage('');
    try {
      const official = await getExamResults(attemptId);
      setResult(official);
      clearEdgeSession(attemptId);
      clearPendingEdgeResult();
      try { window.sessionStorage.removeItem(ACTIVE_ATTEMPT_KEY); } catch { /* no-op */ }
    } catch {
      setMessage('Le résultat officiel n’est pas encore disponible. Le journal reste scellé sur le gateway du centre.');
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    if (!attemptId || !navigator.onLine) return;
    void checkCentralResult();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attemptId]);

  if (!attemptId) {
    return (
      <main className="exam-page">
        <section className="exam-card" style={{ maxWidth: 760, margin: '48px auto' }}>
          <h1>Aucune épreuve Edge en attente</h1>
          <button type="button" className="btn" onClick={() => { window.location.hash = '#/'; }}>Retour à l'accueil</button>
        </section>
      </main>
    );
  }

  if (result) {
    return (
      <main className="exam-page">
        <section className="exam-card" style={{ maxWidth: 760, margin: '48px auto' }}>
          <div className="exam-section-label">Résultat officiel synchronisé</div>
          <h1>{result.passed ? 'ADMIS' : 'AJOURNÉ'}</h1>
          <div style={{ fontSize: 44, fontWeight: 900, margin: '18px 0' }}>{result.score}/{result.total}</div>
          <p className="exam-muted">
            Ce verdict provient du serveur central CodeRoute après vérification et synchronisation du journal Edge.
          </p>
          <button type="button" className="btn" onClick={() => { window.location.hash = '#/'; }}>Retour à l'accueil</button>
        </section>
      </main>
    );
  }

  return (
    <main className="exam-page">
      <section className="exam-card" style={{ maxWidth: 760, margin: '48px auto' }}>
        <div className="exam-section-label">Épreuve finalisée en mode Edge</div>
        <h1>Résultat officiel en attente de synchronisation DNTT</h1>
        <div className="alert aw" role="status" style={{ margin: '18px 0' }}>
          Vos réponses ont été scellées localement sur le gateway du centre. Aucun score ni verdict n'est calculé sur ce poste.
        </div>
        <p className="exam-muted">
          Dès que la connexion du centre revient, le gateway transmet le journal signé au serveur central. Le serveur vérifie la trace, le poste et la deadline avant de calculer le résultat officiel.
        </p>
        {message && <div className="alert aw" role="status">{message}</div>}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 18 }}>
          <button type="button" className="btn" disabled={checking} onClick={() => void checkCentralResult()}>
            {checking ? 'Vérification…' : 'Vérifier la synchronisation'}
          </button>
          <button type="button" className="btn secondary" onClick={() => { window.location.hash = '#/'; }}>Retour à l'accueil</button>
        </div>
        <p className="exam-muted" style={{ marginTop: 16, fontSize: 12 }}>Référence technique : {attemptId}</p>
      </section>
    </main>
  );
}
