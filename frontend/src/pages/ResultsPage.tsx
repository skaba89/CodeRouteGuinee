// ResultsPage — CodeRoute Guinée
// Extrait de src/pages.tsx L3346-L3484
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

export function ResultsPage() {
  const [examSummary, setExamSummary] = useState<ExamSummary>(fallbackExamSummary);
  const [attemptId, setAttemptId] = useState(() => window.localStorage.getItem(DEMO_EXAM_ATTEMPT_STORAGE_KEY) ?? 'demo-attempt-1');
  const [certificateVerification, setCertificateVerification] = useState<ExamCertificateVerification | null>(null);
  const [certificateError, setCertificateError] = useState<string | null>(null);
  const [isVerifyingCertificate, setIsVerifyingCertificate] = useState(false);
  useEffect(() => {
    getExamSummary().then(setExamSummary).catch(() => undefined);
  }, []);

  async function handleCertificateVerification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!attemptId) return;
    setIsVerifyingCertificate(true);
    setCertificateVerification(null);
    setCertificateError(null);
    try {
      if (attemptId.startsWith('demo-')) {
        setCertificateVerification(buildDemoCertificateVerification(attemptId));
        return;
      }
      const result = await verifyExamCertificate(attemptId);
      setCertificateVerification(result);
    } catch {
      setCertificateVerification(buildDemoCertificateVerification(attemptId));
      setCertificateError("API certificat indisponible. Verification demo affichee localement.");
    } finally {
      setIsVerifyingCertificate(false);
    }
  }

  const score = 36;
  const total = 40;
  const threshold = 35;
  const passed = score >= threshold;
  const certificateUrl = attemptId ? getExamCertificatePdfUrl(attemptId) : null;
  const successRate = examSummary.submitted_attempts
    ? Math.round((examSummary.passed_attempts / examSummary.submitted_attempts) * 100)
    : 0;
  const resultChecks = [
    ['Identite candidat', 'Validee'],
    ['Session examen', 'Cloturee'],
    ['Correction', 'Automatique'],
    ['Certificat', passed ? 'Pret' : 'Bloque'],
  ];
  const scoreBreakdown = [
    ['Signalisation', 10, 10],
    ['Priorites', 9, 10],
    ['Securite routiere', 8, 10],
    ['Infractions', 9, 10],
  ];
  const nextSteps = passed
    ? [
        'Validation numerique par le centre agree',
        'Controle administratif du dossier candidat',
        'Transmission vers le circuit de delivrance du permis',
      ]
    : [
        'Notification du candidat',
        'Programmation d une nouvelle session',
        'Revision ciblee sur les themes insuffisants',
      ];
  return (
    <section className="screen results-workspace">
      <div className="results-main">
        <div className="results-header">
          <div>
            <p className="eyebrow dark">Resultat candidat</p>
            <h2>Releve officiel du code de la route</h2>
            <p>Score, admissibilite, verification du certificat et suite administrative reunis dans une vue unique.</p>
          </div>
          <span className={passed ? 'badge ok' : 'badge'}>{passed ? 'Admis' : 'Non admis'}</span>
        </div>
        <div className="result-identity-grid">
          <div className="mini-card">Reference candidat : <strong>GN-CODE-2026-000001</strong></div>
          <div className="mini-card">Session : <strong>Centre Kaloum - 20/06/2026</strong></div>
          <div className="mini-card">Seuil de reussite : <strong>{threshold} / {total}</strong></div>
          <div className="mini-card">Moyenne nationale : <strong>{examSummary.average_score} / {total}</strong></div>
        </div>
        <div className="result-official-grid">
          {resultChecks.map(([label, value]) => (
            <article key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </article>
          ))}
        </div>
        <div className="score-breakdown">
          <h3>Ventilation du score</h3>
          {scoreBreakdown.map(([label, value, max]) => (
            <div className="score-row" key={label}>
              <span>{label}</span>
              <div><i style={{ width: `${(Number(value) / Number(max)) * 100}%` }} /></div>
              <strong>{value} / {max}</strong>
            </div>
          ))}
        </div>
      </div>
      <div className="result-card">
        <span className="result-label">Decision nationale</span>
        <strong>{score} / {total}</strong>
        <p>{passed ? 'Resultat positif. Certificat numerique pret pour validation administrative.' : 'Resultat insuffisant. Nouvelle presentation possible selon les regles nationales.'}</p>
        <div className="metrics compact">
          <article><strong>{formatNumber(examSummary.submitted_attempts)}</strong><span>Examens soumis</span></article>
          <article><strong>{formatNumber(examSummary.passed_attempts)}</strong><span>Admis</span></article>
          <article><strong>{successRate}%</strong><span>Taux de reussite</span></article>
        </div>
        <div className="next-steps-panel">
          <strong>Suite administrative</strong>
          {nextSteps.map((step, index) => (
            <span key={step}><b>{index + 1}</b>{step}</span>
          ))}
        </div>
        <form className="certificate-field" onSubmit={handleCertificateVerification}>
          <label>ID tentative examen<input value={attemptId} onChange={(event) => setAttemptId(event.target.value)} placeholder="Coller l'ID de tentative seedee" /></label>
          <button disabled={isVerifyingCertificate || !attemptId}>{isVerifyingCertificate ? 'Verification...' : 'Verifier certificat'}</button>
        </form>
        {certificateVerification && (
          <div className={certificateVerification.valid ? 'certificate-verification ok' : 'certificate-verification'}>
            <strong>{certificateVerification.valid ? 'Certificat authentique' : 'Certificat non valide'}</strong>
            <span>{certificateVerification.reason ?? certificateVerification.candidate_name ?? certificateVerification.status}</span>
            {certificateVerification.valid && <span>{certificateVerification.center_name} - Score {certificateVerification.score}</span>}
          </div>
        )}
        {certificateError && <p className="form-error">{certificateError}</p>}
        <div className="certificate-trace">
          <span>Empreinte certificat</span>
          <strong>GN-CERT-2026-4F8A-921C</strong>
        </div>
        <div className="actions result-actions">
          <a href="#/candidate">Retour dossier</a>
          <a href="#/admin" className="secondary">Voir supervision</a>
          {certificateUrl && <a href={certificateUrl} target="_blank" rel="noreferrer">Telecharger attestation PDF</a>}
        </div>
      </div>
    </section>
  );
}
