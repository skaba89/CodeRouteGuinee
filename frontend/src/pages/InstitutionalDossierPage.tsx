// InstitutionalDossierPage — CodeRoute Guinée
// Extrait de src/pages.tsx L714-L771
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

export function InstitutionalDossierPage() {
  return (
    <section className="screen dossier-page">
      <div className="dossier-hero">
        <div>
          <p className="eyebrow dark">Dossier institutionnel</p>
          <h2>Presentation Etat - CodeRoute Guinee</h2>
          <p>Support executive pour presenter le pilote, les preuves disponibles, les risques restants et la decision attendue.</p>
        </div>
        <div className="dossier-score">
          <span>Maturite pilote</span>
          <strong>{fallbackInstitutionalReport.readiness_score}%</strong>
          <small>{fallbackInstitutionalReport.readiness_label}</small>
        </div>
      </div>

      <div className="dossier-highlight-grid">
        {dossierHighlights.map(([label, detail]) => (
          <article key={label}>
            <span>{label}</span>
            <p>{detail}</p>
          </article>
        ))}
      </div>

      <div className="dossier-two-columns">
        <section>
          <h3>Perimetre pilote</h3>
          {dossierWorkstreams.map(([label, detail]) => (
            <div className="dossier-line" key={label}>
              <strong>{label}</strong>
              <p>{detail}</p>
            </div>
          ))}
        </section>
        <section>
          <h3>Risques a lever avant production</h3>
          {dossierRisks.map(([label, detail]) => (
            <div className="dossier-line risk" key={label}>
              <strong>{label}</strong>
              <p>{detail}</p>
            </div>
          ))}
        </section>
      </div>

      <div className="dossier-decision">
        <strong>Decision proposee</strong>
        <p>Valider un pilote institutionnel de trois mois avec centres retenus, donnees officielles limitees, supervision nationale et rapport hebdomadaire d avancement.</p>
        <div className="actions result-actions">
          <a href="#/admin">Retour cockpit admin</a>
          <a href="#/admin" className="secondary">Voir roadmap et securite</a>
        </div>
      </div>
    </section>
  );
}
