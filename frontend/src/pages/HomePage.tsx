// HomePage — CodeRoute Guinée
// Extrait de src/pages.tsx L652-L713
// Pour modifier, éditer ce fichier directement.

import { type AuthUser } from '../authClient';
import { type UserRole } from '../auth';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import * as api from '../api';
import {
  buildDemoExamAttempt,
  buildDemoCertificateVerification,
  buildDemoQuestionImage,
  filterDemoIdentityChecks,
  filterDemoSubmissions,
  filterDemoAuditLogs,
  filterDemoMonitoring,
  filterDemoPayments,
  buildDemoImportStatus,
  buildRiskLabel,
  formatNumber,
  formatCurrency,
  formatAuditDetails,
  getActionErrorMessage,
  sanitizePaymentFilters,
  downloadLocalFile,
  type AuditLogEntry,
  type AuditLogFilters,
  type CandidateIdentityCheck,
  type CandidateIdentityFilters,
  type CandidateSubmission,
  type CandidateSubmissionFilters,
  type ExamAttempt,
  type ExamCertificateVerification,
  type ExamMonitoringFilters,
  type PaymentFilters,
} from './helpers';

export function HomePage() {
  const [dashboard, setDashboard] = useState<DashboardData>(fallbackDashboard);
  const [readiness, setReadiness] = useState<OperationalReadiness>(fallbackOperationalReadiness);
  const [apiStatus, setApiStatus] = useState<'connected' | 'offline'>('offline');

  useEffect(() => {
    getDashboard()
      .then((data) => {
        setDashboard(data);
        setApiStatus('connected');
      })
      .catch(() => setApiStatus('offline'));
    getOperationalReadiness().then(setReadiness).catch(() => undefined);
  }, []);

  const metrics = [
    { label: 'Candidats inscrits', value: formatNumber(dashboard.candidates) },
    { label: 'Centres agrees', value: formatNumber(dashboard.accredited_centers) },
    { label: 'Sessions organisees', value: formatNumber(dashboard.exam_sessions) },
    { label: 'Alertes entree', value: formatNumber(dashboard.fraud_alerts) },
  ];

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Produit national pour la Guinee</p>
          <h1>CodeRoute Guinee</h1>
          <p>Plateforme nationale de digitalisation, securisation et tracabilite des examens du code de la route.</p>
          <div className="actions">
            <a href="http://localhost:8000/docs" target="_blank">Voir l'API</a>
            <a href="#/center" className="secondary">Controle centre</a>
          </div>
        </div>
        <div className="hero-status">
          <span>Convocation QR</span><strong>Actif</strong>
          <span>Paiement Mobile Money</span><strong>Sandbox</strong>
          <span>Controle entree</span><strong>Actif</strong>
          <span>API frontend</span><strong>{apiStatus === 'connected' ? 'Connectee' : 'Fallback'}</strong>
          <span>Readiness</span><strong>{readiness.status === 'ready' ? 'Prete' : 'A verifier'}</strong>
        </div>
      </section>

      <section className="metrics">
        {metrics.map((metric) => (
          <article key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
          </article>
        ))}
      </section>

      <section className="panel">
        <h2>Socle fonctionnel national</h2>
        <div className="grid modules-grid">
          {modules.map((module) => <div className="card" key={module}>{module}</div>)}
        </div>
      </section>
    </>
  );
}
