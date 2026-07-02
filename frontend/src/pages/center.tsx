// CenterPage — CodeRoute Guinée
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

export function CenterPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAct = canUseProtectedActions(currentUser, isPresentationMode, ['center','admin','super_admin']);

  const [entryRef, setEntryRef] = useState('');
  const [verifCode, setVerifCode] = useState('');
  const [centerCode, setCenterCode] = useState('');
  const [centers, setCenters] = useState<Center[]>([]);
  const [entryResult, setEntryResult] = useState<EntryValidationResult | null>(null);
  const [entryErr, setEntryErr] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  const [bookingRef, setBookingRef] = useState('');
  const [deviceKey, setDeviceKey] = useState('POSTE-01');
  const [attempt, setAttempt] = useState<ExamAttempt | null>(null);
  const [startErr, setStartErr] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const [incidents, setIncidents] = useState<CenterIncident[]>([]);
  const [incType, setIncType] = useState('technical_issue');
  const [incDesc, setIncDesc] = useState('');
  const [incSev, setIncSev] = useState('medium');
  const [incErr, setIncErr] = useState<string | null>(null);
  const [reporting, setReporting] = useState(false);

  useEffect(() => {
    getCenters().then(r => {
      setCenters(r.items);
      // Pré-sélectionner le centre de l'agent connecté si disponible
      if (currentUser?.center_id) {
        const myCenter = r.items.find((c: { id: string; code: string }) => c.id === currentUser.center_id);
        if (myCenter) setCenterCode(myCenter.code);
      }
    }).catch(() => undefined);
    getCenterIncidents({ statusFilter: 'open', limit: 10 }).then(r => setIncidents(r.items)).catch(() => undefined);
  }, [currentUser]);

  async function handleEntry(e: FormEvent) {
    e.preventDefault();
    setScanning(true); setEntryErr(null); setEntryResult(null);
    try {
      const r = await validateEntry({ reference: entryRef, verification_code: verifCode, center_code: centerCode });
      setEntryResult(r);
    } catch (err) {
      setEntryErr(errMsg(err, 'Validation impossible.'));
    } finally { setScanning(false); }
  }

  async function handleStartExam(e: FormEvent) {
    e.preventDefault();
    setStarting(true); setStartErr(null); setAttempt(null);
    try {
      const r = await startExamFromBooking(bookingRef, deviceKey, deviceKey);
      setAttempt(r);
    } catch (err) {
      setStartErr(errMsg(err, 'Impossible de démarrer l\'examen.'));
    } finally { setStarting(false); }
  }

  async function handleIncident(e: FormEvent) {
    e.preventDefault();
    if (!canAct) { setIncErr('Connectez-vous pour déclarer un incident officiel.'); return; }
    const center = centers.find(c => c.code === centerCode);
    if (!center) { setIncErr('Code centre introuvable.'); return; }
    setReporting(true); setIncErr(null);
    try {
      await reportCenterIncident({ center_id: center.id, incident_type: incType, severity: incSev, description: incDesc });
      setIncErr(null); setIncDesc('');
      getCenterIncidents({ statusFilter: 'open', limit: 10 }).then(r => setIncidents(r.items)).catch(() => undefined);
      alert('Incident déclaré avec succès.');
    } catch (err) {
      setIncErr(errMsg(err, 'Déclaration échouée.'));
    } finally { setReporting(false); }
  }

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Espace centre</span>
        <h1>Gestion des examens</h1>
        <p>Validez les entrées, démarrez les examens et gérez les incidents.</p>
      </div>

      {!canAct && (
        <div className="alert aw" style={{ marginBottom: 20 }}>
          Connectez-vous avec un compte <strong>center</strong> pour utiliser les fonctionnalités réelles.
        </div>
      )}

      <div className="g2">
        {/* Validation entrée */}
        <div className="card">
          <div className="card-header"><span className="card-title"> Valider l'entrée candidat</span></div>
          <form onSubmit={handleEntry} style={{ display: 'grid', gap: 12 }}>
            <label>
              Code centre
              {centers.length > 0 ? (
                <select value={centerCode} onChange={e => setCenterCode(e.target.value)}>
                  <option value="">— Sélectionner un centre —</option>
                  {centers.map(c => <option key={c.id} value={c.code}>{c.name}</option>)}
                </select>
              ) : (
                <input value={centerCode} onChange={e => setCenterCode(e.target.value)} placeholder="CRG-CONAKRY-KALOUM-001" />
              )}
            </label>
            <label>Référence de réservation<input value={entryRef} onChange={e => setEntryRef(e.target.value)} placeholder="GN-CONV-2026-000001" /></label>
            <label>Code de vérification<input value={verifCode} onChange={e => setVerifCode(e.target.value)} placeholder="GN-CONV-..." /></label>
            {entryErr && <p className="form-error">{entryErr}</p>}
            {entryResult && (
              <div className={`scanner-result${entryResult.allowed ? '' : ' denied'}`}>
                <div className="scanner-icon" style={{ color: entryResult.allowed ? 'var(--guinea-green)' : 'var(--red)' }}>
                  {entryResult.allowed
                    ? <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    : <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                  }
                </div>
                <strong style={{ fontSize: 16 }}>{entryResult.allowed ? 'ENTRÉE AUTORISÉE' : 'ENTRÉE REFUSÉE'}</strong>
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>{entryResult.message ?? entryResult.reason ?? ''}</span>
              </div>
            )}
            <button type="submit" className="btn-primary" disabled={scanning || !entryRef || !verifCode}>
              {scanning ? 'Validation…' : 'Valider l\'entrée'}
            </button>
          </form>
        </div>

        {/* Démarrer examen */}
        <div className="card">
          <div className="card-header"><span className="card-title">Démarrer un examen</span></div>
          <form onSubmit={handleStartExam} style={{ display: 'grid', gap: 12 }}>
            <label>Référence de réservation<input value={bookingRef} onChange={e => setBookingRef(e.target.value)} placeholder="GN-CONV-2026-000001" /></label>
            <label>Code du poste<input value={deviceKey} onChange={e => setDeviceKey(e.target.value)} placeholder="POSTE-01" /></label>
            {startErr && <p className="form-error">{startErr}</p>}
            {attempt && (
              <div className="alert as">
                 Examen démarré — ID : <code style={{ fontSize: 11 }}>{attempt.id}</code>
                <a href="#/exam" style={{ marginLeft: 8 }}><button type="button" className="btn-sm btn-success">Ouvrir l'examen →</button></a>
              </div>
            )}
            <button type="submit" className="btn-success" disabled={starting || !bookingRef}>
              {starting ? 'Démarrage…' : 'Démarrer l\'examen'}
            </button>
          </form>
        </div>

        {/* Incidents */}
        <div className="card">
          <div className="card-header"><span className="card-title">Déclarer un incident</span></div>
          <form onSubmit={handleIncident} style={{ display: 'grid', gap: 12 }}>
            <label>
              Type d'incident
              <select value={incType} onChange={e => setIncType(e.target.value)}>
                <option value="technical_issue">Problème technique</option>
                <option value="candidate_cheating">Tentative de fraude</option>
                <option value="power_outage">Coupure de courant</option>
                <option value="medical_emergency">Urgence médicale</option>
                <option value="other">Autre</option>
              </select>
            </label>
            <label>
              Gravité
              <select value={incSev} onChange={e => setIncSev(e.target.value)}>
                <option value="low">Faible</option>
                <option value="medium">Moyenne</option>
                <option value="high">Haute</option>
                <option value="critical">Critique</option>
              </select>
            </label>
            <label>Description<textarea value={incDesc} onChange={e => setIncDesc(e.target.value)} placeholder="Décrivez l'incident…" /></label>
            {incErr && <p className="form-error">{incErr}</p>}
            <button type="submit" className="btn-danger" disabled={reporting || !incDesc.trim()}>
              {reporting ? 'Envoi…' : 'Déclarer l\'incident'}
            </button>
          </form>
        </div>

        {/* Incidents ouverts */}
        <div className="card">
          <div className="card-header">
            <span className="card-title"> Incidents ouverts ({incidents.length})</span>
            <button className="btn-sm secondary-button" onClick={() => getCenterIncidents({ statusFilter: 'open', limit: 25 }).then(r => setIncidents(r.items)).catch(() => undefined)}>
              Actualiser
            </button>
          </div>
          {incidents.length === 0 ? (
            <div className="empty-state"><p>Aucun incident en cours </p></div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Type</th><th>Gravité</th><th>Statut</th></tr></thead>
                <tbody>
                  {incidents.map(inc => (
                    <tr key={inc.id}>
                      <td>{inc.incident_type}</td>
                      <td>
                        <span className={`badge ${inc.severity === 'critical' ? 'br' : inc.severity === 'high' ? 'bgo' : 'bgr'}`}>
                          {inc.severity}
                        </span>
                      </td>
                      <td><span className="badge bgr">{inc.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Gestion avancée du centre */}
      <div className="g2" style={{ marginTop: 16 }}>
        <CenterManagementPanel center={centers.find(c => c.code === centerCode) ?? null} />
        <DeviceAlertsPanel centerId={centers.find(c => c.code === centerCode)?.id} />
      </div>

    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// ADMIN PAGE — Tableau de bord administration
// ══════════════════════════════════════════════════════════════════
