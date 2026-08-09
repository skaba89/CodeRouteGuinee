import { useEffect, useState } from 'react';
import { claimPendingEdgeSession, hasPendingEdgeBootstrap } from '../edgeExamSession';
import { ExamPage } from './exam';

export default function EdgeExamEntry() {
  const [state, setState] = useState<'checking' | 'ready' | 'error'>(
    hasPendingEdgeBootstrap() ? 'checking' : 'ready',
  );
  const [error, setError] = useState('');

  const claim = async () => {
    if (!hasPendingEdgeBootstrap()) {
      setState('ready');
      return;
    }
    setState('checking');
    setError('');
    try {
      await claimPendingEdgeSession();
      setState('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible d'activer la session Edge.");
      setState('error');
    }
  };

  useEffect(() => {
    void claim();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (state === 'ready') return <ExamPage />;

  return (
    <main className="exam-page">
      <section className="exam-card" style={{ maxWidth: 720, margin: '48px auto' }}>
        <div className="exam-section-label">Continuité centre</div>
        <h1>{state === 'checking' ? 'Activation du mode Edge…' : 'Activation Edge impossible'}</h1>
        {state === 'checking' ? (
          <p className="exam-muted">Vérification du gateway local et liaison sécurisée avec ce poste candidat.</p>
        ) : (
          <>
            <div className="alert ar" role="alert">{error}</div>
            <p className="exam-muted">
              Vérifiez que ce poste est bien celui enregistré dans le centre puis réessayez.
            </p>
            <button type="button" className="btn" onClick={() => void claim()}>
              Réessayer l'activation
            </button>
          </>
        )}
      </section>
    </main>
  );
}
