import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[CodeRoute] Erreur non gérée:', error, info.componentStack);
    try {
      // Envoyer à Sentry si disponible
      const w = window as unknown as { Sentry?: { captureException: (e: Error) => void } };
      w.Sentry?.captureException(error);
    } catch {}
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', alignItems: 'center',
          justifyContent: 'center', padding: 24, background: '#F9FAFB',
        }}>
          <div style={{
            background: '#fff', border: '1px solid #E4E7EC', borderRadius: 16,
            padding: '32px 40px', maxWidth: 500, textAlign: 'center',
            boxShadow: '0 16px 32px rgba(10,37,64,.12)',
          }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#0A2540', marginBottom: 8 }}>
              Une erreur inattendue s'est produite
            </h2>
            <p style={{ fontSize: 13, color: '#667085', marginBottom: 20 }}>
              {this.state.error.message || 'Erreur inconnue.'}
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button
                onClick={() => this.setState({ error: null })}
                style={{ background: '#0066CC', color: '#fff', border: 'none',
                  borderRadius: 8, padding: '10px 20px', cursor: 'pointer',
                  fontSize: 13, fontWeight: 600 }}>
                Réessayer
              </button>
              <button
                onClick={() => { window.location.hash = '#/'; this.setState({ error: null }); }}
                style={{ background: '#F9FAFB', color: '#344054', border: '1px solid #E4E7EC',
                  borderRadius: 8, padding: '10px 20px', cursor: 'pointer',
                  fontSize: 13, fontWeight: 500 }}>
                Retour à l'accueil
              </button>
            </div>
            {(import.meta as {env?: {DEV?: boolean}}).env?.DEV && (
              <details style={{ marginTop: 20, textAlign: 'left' }}>
                <summary style={{ fontSize: 12, color: '#667085', cursor: 'pointer' }}>
                  Détails techniques (dev)
                </summary>
                <pre style={{ fontSize: 11, color: '#D32F2F', marginTop: 8,
                  overflow: 'auto', background: '#FFF5F5', padding: 10, borderRadius: 6 }}>
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
