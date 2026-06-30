// DrivingSchoolPage — CodeRoute Guinée
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

export function DrivingSchoolPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const isSchool = currentUser?.role === 'driving_school';

  const MOCK_STUDENTS = [
    { id:'1', name:'Mamadou Diallo',    score:32, sessions:8,  status:'en_cours',  progress:80 },
    { id:'2', name:'Fatoumata Camara',  score:28, sessions:5,  status:'risque',    progress:55 },
    { id:'3', name:'Alpha Bah',         score:38, sessions:12, status:'pret',      progress:95 },
    { id:'4', name:'Mariam Soumah',     score:35, sessions:9,  status:'pret',      progress:88 },
    { id:'5', name:'Ibrahima Kouyaté',  score:22, sessions:3,  status:'debutant',  progress:30 },
    { id:'6', name:'Kadiatou Sylla',    score:30, sessions:6,  status:'en_cours',  progress:65 },
  ];

  const pret = MOCK_STUDENTS.filter(s=>s.status==='pret').length;
  const risque = MOCK_STUDENTS.filter(s=>s.status==='risque').length;

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Portail Auto-École</span>
        <h1>Tableau de bord pédagogique</h1>
        <p>Suivez les progrès de vos élèves et identifiez ceux qui ont besoin d'aide.</p>
      </div>

      {!isSchool && (
        <div className="alert aw" style={{ marginBottom: 20 }}>
           Mode démonstration — Connectez-vous avec un compte auto-école pour voir vos élèves réels.
        </div>
      )}

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card s-blue">
          <div className="stat-label">Élèves inscrits</div>
          <div className="stat-value">{MOCK_STUDENTS.length}</div>
        </div>
        <div className="stat-card s-green">
          <div className="stat-label">Prêts pour l'examen</div>
          <div className="stat-value">{pret}</div>
          <div className="stat-sub">score ≥ 35/40</div>
        </div>
        <div className="stat-card s-red">
          <div className="stat-label">Nécessitent de l'aide</div>
          <div className="stat-value">{risque}</div>
          <div className="stat-sub">score &lt; 28/40</div>
        </div>
        <div className="stat-card s-gold">
          <div className="stat-label">Score moyen</div>
          <div className="stat-value">{Math.round(MOCK_STUDENTS.reduce((s,e)=>s+e.score,0)/MOCK_STUDENTS.length)}</div>
          <div className="stat-sub">sur 40</div>
        </div>
      </div>

      {/* Tableau élèves */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">👥 Suivi individuel des élèves</span>
          <a href="#/training"><button className="secondary-button btn-sm">+ Affecter des exercices</button></a>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Élève</th>
                <th>Sessions</th>
                <th>Score moyen</th>
                <th>Progression</th>
                <th>Statut</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_STUDENTS.map(s => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td>{s.sessions} séances</td>
                  <td>
                    <span style={{ fontWeight: 700, color: s.score >= 35 ? 'var(--green)' : s.score >= 30 ? 'var(--gold)' : 'var(--red)' }}>
                      {s.score}/40
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: s.progress >= 80 ? 'var(--green)' : s.progress >= 60 ? 'var(--gold)' : 'var(--red)', width: `${s.progress}%`, borderRadius: 'inherit' }} />
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', minWidth: 32 }}>{s.progress}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${s.status==='pret'?'bg':s.status==='risque'?'br':s.status==='en_cours'?'bb':'bgr'}`}>
                      {s.status==='pret' ? ' Prêt' : s.status==='risque' ? '️ Risque' : s.status==='en_cours' ? '📈 En cours' : '🆕 Débutant'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="secondary-button btn-sm" style={{ fontSize: 11 }}>📊 Rapport</button>
                      {s.status === 'risque' && (
                        <button className="btn-sm btn-gold" style={{ fontSize: 11 }}>📞 Contacter</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recommandations */}
      {risque > 0 && (
        <div className="alert aw">
          ️ <strong>{risque} élève(s) en difficulté</strong> — Leur score moyen est inférieur à 28/40.
          Planifiez des sessions supplémentaires sur les catégories Priorités et Signalisation.
        </div>
      )}

      <div className="g2">
        <div className="card">
          <div className="card-header"><span className="card-title">📅 Prochaines sessions</span></div>
          <div style={{ display: 'grid', gap: 10 }}>
            {[
              { date: '22/06/2026', time: '09h00', students: 4, center: 'CTR-KALOUM' },
              { date: '25/06/2026', time: '14h00', students: 3, center: 'CTR-MATAM' },
              { date: '28/06/2026', time: '09h00', students: 5, center: 'CTR-KALOUM' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--bg)', borderRadius: 'var(--r)', fontSize: 13 }}>
                <div style={{ textAlign: 'center', minWidth: 48 }}>
                  <div style={{ fontWeight: 800, color: 'var(--ink)' }}>{s.date.split('/')[0]}</div>
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{s.date.split('/')[1]+'/'+s.date.split('/')[2]}</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{s.time} — {s.center}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>{s.students} élèves inscrits</div>
                </div>
                <span className="badge bb">{s.students} candidats</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title"> Actions rapides</span></div>
          <div style={{ display: 'grid', gap: 10 }}>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
              ➕ Inscrire un nouvel élève
            </button>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
              📥 Importer liste (CSV)
            </button>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
              📊 Rapport mensuel PDF
            </button>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
              📅 Réserver des sessions examen
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// MINISTERIAL PAGE — Portail ministériel (Mois 13–18)
// Accessible depuis AdminPage onglet "Ministère"
// ══════════════════════════════════════════════════════════════════
