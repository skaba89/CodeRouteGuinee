// ResultsPage — CodeRoute Guinée
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

export function ResultsPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAct = canUseProtectedActions(currentUser, isPresentationMode, ['candidate','center','admin','super_admin']);

  const [attemptId, setAttemptId] = useState('');
  const [result, setResult] = useState<ExamDetailedResult | null>(null);
  const [cert, setCert] = useState<ExamCertificateVerification | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all'|'ok'|'ko'>('all');

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!attemptId.trim()) return;
    setLoading(true); setErr(null); setResult(null); setCert(null);
    try {
      const [r, c] = await Promise.allSettled([
        getExamResults(attemptId),
        verifyExamCertificate(attemptId),
      ]);
      if (r.status === 'fulfilled') setResult(r.value);
      if (c.status === 'fulfilled') setCert(c.value);
      if (r.status === 'rejected' && c.status === 'rejected') setErr('Identifiant introuvable.');
    } catch {
      setErr('Identifiant introuvable.');
    } finally { setLoading(false); }
  }

  const filtered = result?.questions.filter(q =>
    filter === 'all' ? true : filter === 'ok' ? q.is_correct : !q.is_correct
  ) ?? [];

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Résultats</span>
        <h1>Résultats & Certificats</h1>
        <p>Consultez les résultats d'un examen et vérifiez l'authenticité d'un certificat.</p>
      </div>

      <div style={{ maxWidth: 600 }}>
        <form onSubmit={handleSearch} className="card" style={{ display: 'grid', gap: 14 }}>
          <label>
            Identifiant de tentative
            <input value={attemptId} onChange={e => setAttemptId(e.target.value)} placeholder="ATT-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
          </label>
          {err && <p className="form-error">{err}</p>}
          <button type="submit" className="btn-primary" disabled={loading || !attemptId.trim()}>
            {loading ? 'Recherche…' : '🔍 Rechercher'}
          </button>
        </form>
      </div>

      {cert && (
        <div style={{ maxWidth: 600, marginTop: 16 }}>
          <div className={`alert ${cert.valid && cert.passed ? 'as' : cert.valid ? 'aw' : 'ae'}`}>
            <span style={{ fontSize: 24 }}>{cert.valid && cert.passed ? '🏆' : cert.valid ? '📋' : '❌'}</span>
            <div>
              <strong>{cert.valid && cert.passed ? 'ADMIS — Certificat valide' : cert.valid ? 'AJOURNÉ' : 'Certificat invalide'}</strong>
              {cert.candidate_name && <div style={{ fontSize: 12, marginTop: 2 }}>{cert.candidate_name} {cert.score !== undefined ? `· ${cert.score}/40` : ''}</div>}
              {cert.valid && cert.passed && (
                <button type="button" className="btn-sm btn-success" style={{ marginTop: 8 }}
                  onClick={() => { window.open(getExamCertificatePdfUrl(attemptId), '_blank', 'noopener'); }}>
                  ⬇ Télécharger le certificat PDF
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {result && (
        <div style={{ maxWidth: 720, marginTop: 20, display: 'grid', gap: 14 }}>
          <div style={{ background: `linear-gradient(135deg,${result.passed ? 'var(--green)' : 'var(--navy)'},${result.passed ? '#006b47' : 'var(--navy2)'})`, borderRadius: 16, padding: '20px 24px', color: '#fff', display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 40 }}>{result.passed ? '🏆' : '📋'}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 18, fontWeight: 800 }}>{result.passed ? 'Admis' : 'Ajourné'}</div>
              <div style={{ fontSize: 12, opacity: .75 }}>{result.candidate_name}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 32, fontWeight: 900 }}>{result.score}/{result.total}</div>
              <div style={{ fontSize: 12, opacity: .75 }}>{result.score_percent}%</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(['all','ok','ko'] as const).map(f => (
              <button key={f} type="button"
                className={filter === f ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
                onClick={() => setFilter(f)}>
                {f === 'all' ? `Toutes (${result.questions.length})`
                  : f === 'ok' ? `✅ Correctes (${result.questions.filter(q => q.is_correct).length})`
                  : `❌ Incorrectes (${result.questions.filter(q => !q.is_correct).length})`}
              </button>
            ))}
          </div>

          {filtered.map(q => (
            <div key={q.question_id} style={{ background: 'var(--surface, #fff)', border: `1.5px solid ${q.is_correct ? '#86efac' : '#fca5a5'}`, borderRadius: 12, padding: '14px 16px', display: 'grid', gap: 7 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ background: 'var(--bg)', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>Q{q.number}</span>
                <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--muted)', flex: 1 }}>{q.category}</span>
                <span>{q.is_correct ? '✅' : '❌'}</span>
              </div>
              <p style={{ fontWeight: 600, fontSize: 13, margin: 0 }}>{q.text}</p>
              {!q.is_correct && q.given_answer && <p style={{ fontSize: 12, color: 'var(--red, #D32F2F)', margin: 0 }}>Votre réponse : <strong>{q.given_answer}</strong></p>}
              {!q.is_correct && <p style={{ fontSize: 12, color: 'var(--green)', margin: 0 }}>Bonne réponse : <strong>{q.correct_answer}</strong></p>}
              {q.explanation && <p style={{ fontSize: 12, color: 'var(--muted)', background: 'var(--bg)', padding: '6px 10px', borderRadius: 8, margin: 0 }}>💡 {q.explanation}</p>}
            </div>
          ))}
        </div>
      )}

    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// TRAINING PAGE — Mode entraînement libre (Mois 4–6)
// ══════════════════════════════════════════════════════════════════
