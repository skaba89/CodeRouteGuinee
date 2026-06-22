// HomePage — CodeRoute Guinée
import { type FormEvent, useEffect, useRef, useCallback, useState } from 'react';
import { AudioModeBanner, LocaleAudioSwitcher, PlayButton, AudioToggle } from '../components/AudioButton';
import {
  InstitutionalAuthsPanel,
  DeviceAlertsPanel,
  CenterManagementPanel,
  QuestionsAdminPanel,
  CandidateIdentityForm,
  CandidateRecourseForm,
  CertificatePdfButton,
  CsvExportsPanel,
  OfficialPaymentsImportPanel,
} from '../components/AdminExtras';
import { Pagination, SearchBar, PaginationBar, PageSizeSelector } from '../components/Pagination';
import {
  type CandidateFilters,
  type CenterFilters,
  type QuestionFilters,
  type UserFilters,
} from '../api';
import { isAudioLocale, speakFeedback, stop as stopAudio } from '../audio';
import { type Locale } from '../i18n';
import { type AuthUser } from '../authClient';
import { type UserRole } from '../auth';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import {
  type Center, type Candidate, type DashboardData, type ExamSummary,
  type EntrySummary, type ExamAttempt, type EntryValidationResult,
  type PaymentResult, type PaymentFilters, type AuditLogEntry, type AuditLogFilters,
  type CenterIncident, type InstitutionalUser, type InstitutionalUserCreatePayload,
  type ExamCertificateVerification, type ExamDetailedResult, type ExamLiveStatus,
  type CandidateIdentityCheck, type CandidateSubmission,
  type ExamMonitoringSummary, type ExamMonitoringEvent, type ExamMonitoringFilters,
  type QuestionGovernanceItem,
  getDashboard, getCandidates, getCenters, getExamSummary, getEntrySummary,
  getAuditLogs, getAdminPaymentSummary, getPaymentReconciliationItems,
  getInstitutionalUsers, createInstitutionalUser,
  updateInstitutionalUserRole, updateInstitutionalUserStatus,
  resetInstitutionalUserPassword,
  validateEntry, reportCenterIncident, getCenterIncidents, resolveCenterIncident,
  createPayment, getConvocationPdfUrl, verifyExamCertificate,
  downloadExamCertificatePdf, getExamResults,
  startExamFromBooking, submitExamAttempt, getExamLiveStatus,
  getCandidateIdentityChecks, getCandidateSubmissions,
  getExamMonitoringSummaries, getExamMonitoringEvents,
  getQuestionGovernanceItems, decideQuestionGovernance,
  getPaymentAlerts, getInstitutionalReport, downloadInstitutionalReportPdf,
  downloadDashboardCsv, downloadAuditLogsCsv, downloadExamAttemptsCsv,
  downloadAdminPaymentsCsv, decideCandidateIdentity, handleCandidateSubmission,
  type OperationsSummary,
  type InstitutionalReadiness,
  type InstitutionalActionCenter,
  type InstitutionalActionItem,
  type CenterStation,
  getOperationsSummary,
  getInstitutionalReadiness,
  getInstitutionalActionCenter,
  downloadInstitutionalReportCsv,
  importOfficialCandidates,
  importOfficialCenters,
  importOfficialQuestions,
  getCenterStations,
  createCenterStation,
  getExamCertificatePdfUrl,
} from '../api';
import { DEMO_QUESTIONS } from '../pages/examQuestions';

// ── Helpers ───────────────────────────────────────────────────────
function fmt(n: number) { return n.toLocaleString('fr-FR'); }
function fmtGNF(n: number) { return `${fmt(n)} GNF`; }
function fmtDate(s: string) { return new Date(s).toLocaleDateString('fr-FR'); }
function errMsg(e: unknown, fallback = 'Erreur inattendue'): string {
  if (e instanceof Error) return e.message;
  if (typeof e === 'object' && e !== null && 'detail' in e) return String((e as { detail: unknown }).detail);
  return fallback;
}

// ══════════════════════════════════════════════════════════════════
// HOME PAGE — Accueil toutes rôles
// ══════════════════════════════════════════════════════════════════

export function HomePage() {
  const { currentUser, isPresentationMode, role } = useAuthSession();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => undefined);
  }, []);

  const isAdmin = role === 'admin' || role === 'super_admin';
  const isCenter = role === 'center';
  const isCandidate = role === 'candidate';

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="dash-hero">
        <div>
          <span className="eyebrow" style={{ color: 'rgba(255,255,255,.6)' }}>Plateforme nationale</span>
          <h1>
            {isPresentationMode
              ? 'Bienvenue sur CodeRoute Guinée'
              : `Bonjour, ${currentUser?.full_name?.split(' ')[0] ?? 'Agent'} 👋`}
          </h1>
          <p>Examen officiel du code de la route — République de Guinée</p>
        </div>
        <div className="dash-hero-flag">🇬🇳</div>
      </div>

      {isAdmin && dashboard && (
        <div className="stats-grid">
          <div className="stat-card s-blue">
            <div className="stat-label">Candidats</div>
            <div className="stat-value">{fmt(dashboard.candidates)}</div>
            <div className="stat-sub">inscrits</div>
          </div>
          <div className="stat-card s-green">
            <div className="stat-label">Centres agréés</div>
            <div className="stat-value">{fmt(dashboard.accredited_centers)}</div>
          </div>
          <div className="stat-card s-gold">
            <div className="stat-label">Sessions</div>
            <div className="stat-value">{fmt(dashboard.exam_sessions)}</div>
          </div>
          <div className="stat-card s-red">
            <div className="stat-label">Alertes fraude</div>
            <div className="stat-value">{fmt(dashboard.fraud_alerts)}</div>
          </div>
        </div>
      )}

      <div className="g2">
        {isAdmin && (
          <>
            <div className="card">
              <div className="card-header"><span className="card-title">📊 Administration</span></div>
              <div className="actions">
                <a href="#/admin"><button className="btn-primary btn-sm">Tableau de bord admin</button></a>
                <a href="#/dossier"><button className="secondary-button btn-sm">Dossier institutionnel</button></a>
                <a href="#/results"><button className="secondary-button btn-sm">Résultats & certificats</button></a>
              </div>
            </div>
            <div className="card">
              <div className="card-header"><span className="card-title">⚡ Actions rapides</span></div>
              <div style={{ marginTop: 12 }}>
                <CsvExportsPanel />
              </div>
            </div>
          </>
        )}

        {isCenter && (
          <div className="card">
            <div className="card-header"><span className="card-title">🏢 Espace centre</span></div>
            <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
              Gérez les entrées, démarrez les examens et déclarez les incidents.
            </p>
            <a href="#/center"><button className="btn-primary">Accéder à l'espace centre →</button></a>
          </div>
        )}

        {isCandidate && (
          <div className="card">
            <div className="card-header"><span className="card-title">🎓 Espace candidat</span></div>
            <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
              Suivez votre dossier, payez votre examen et téléchargez votre convocation.
            </p>
            <a href="#/candidate"><button className="btn-primary">Mon espace candidat →</button></a>
          </div>
        )}

        <div className="card">
          <div className="card-header"><span className="card-title">📋 Examen code de la route</span></div>
          <div style={{ display: 'grid', gap: 8, fontSize: 13, color: 'var(--ink2)', marginBottom: 14 }}>
            <div>⏱ 30 minutes • 40 questions tirées sur 200</div>
            <div>✅ Seuil d'admission : 35/40 (87,5 %)</div>
            <div>📱 Questions illustrées par catégorie</div>
          </div>
          <a href="#/exam"><button className="btn-success">Passer l'examen →</button></a>
        </div>
      </div>

      {/* Formulaires dossier candidat */}
      <div className="g2" style={{ marginTop: 16 }}>
        <CandidateIdentityForm candidateId={currentUser?.id} />
        <CandidateRecourseForm candidateId={currentUser?.id} />
      </div>

    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// CANDIDATE PAGE — Espace candidat complet
// ══════════════════════════════════════════════════════════════════
