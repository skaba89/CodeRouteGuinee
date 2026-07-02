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
  getMyCandidateProfile, getMyBookings, type MyBooking,
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

export function CandidatePage() {
  const { currentUser, isPresentationMode } = useAuthSession();

  const canAct = canUseProtectedActions(currentUser, isPresentationMode, ['candidate','admin','super_admin']);

  const [bookRef, setBookRef] = useState('');
  const [provider, setProvider] = useState('orange_money');
  const [phone, setPhone] = useState('+224620000000');
  const [amount] = useState(250_000);
  const [paying, setPaying] = useState(false);
  const [payResult, setPayResult] = useState<PaymentResult | null>(null);
  const [payErr, setPayErr] = useState<string | null>(null);

  const [certId, setCertId] = useState('');
  const [myBookings, setMyBookings] = useState<MyBooking[]>([]);
  const [myBookingsLoaded, setMyBookingsLoaded] = useState(false);

  // Charger les réservations du candidat connecté
  useEffect(() => {
    if (currentUser?.role === 'candidate' && !myBookingsLoaded) {
      getMyBookings()
        .then(bks => { setMyBookings(bks); setMyBookingsLoaded(true); })
        .catch(() => setMyBookingsLoaded(true));
    }
  }, [currentUser, myBookingsLoaded]);
  const [cert, setCert] = useState<ExamCertificateVerification | null>(null);
  const [certErr, setCertErr] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function handlePay(e: FormEvent) {
    e.preventDefault();
    if (!bookRef.trim()) { setPayErr('Saisissez votre référence de réservation.'); return; }
    setPaying(true); setPayErr(null); setPayResult(null);
    try {
      const r = await createPayment({ booking_reference: bookRef, amount_gnf: amount, provider, phone });
      setPayResult(r);
      // Pour Wave : ouvrir l'URL de checkout dans un nouvel onglet / deep link
      if (r.checkout_url && provider === 'wave') {
        window.open(r.checkout_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err) {
      setPayErr(errMsg(err, 'Paiement impossible — vérifiez votre réservation et votre solde.'));
    } finally { setPaying(false); }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    if (!certId.trim()) return;
    setChecking(true); setCert(null); setCertErr(null);
    try {
      const r = await verifyExamCertificate(certId);
      setCert(r);
    } catch {
      setCertErr('Certificat introuvable. Vérifiez l\'identifiant.');
    } finally { setChecking(false); }
  }

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Espace candidat</span>
        <h1>Mon dossier</h1>
        <p>Suivez votre parcours, payez et téléchargez votre convocation.</p>
      </div>

      {/* Réservations du candidat pilote */}
      {myBookings.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><span className="card-title">Mes réservations</span></div>
          <div style={{ display: 'grid', gap: 10, marginTop: 4 }}>
            {myBookings.map(bk => (
              <div key={bk.reference} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg)', borderRadius: 'var(--r)', fontSize: 13 }}>
                <div>
                  <strong style={{ color: 'var(--ink)', fontFamily: 'var(--font-ui)', letterSpacing: '.01em' }}>{bk.reference}</strong>
                  <span style={{ color: 'var(--muted)', marginLeft: 12 }}>{bk.session_date ?? bk.status}</span>
                </div>
                <button className="btn-sm btn-outline" onClick={() => setBookRef(bk.reference)}>
                  Utiliser
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Étapes */}
      <div className="steps">
        {[
          { n: 1, label: 'Inscription', sub: 'Profil enregistré' },
          { n: 2, label: 'Réservation', sub: 'Session choisie', cls: bookRef ? 'done' : '' },
          { n: 3, label: 'Paiement', sub: payResult?.status === 'paid' ? 'Réglé' : 'En attente', cls: payResult?.status === 'paid' ? 'done' : bookRef ? 'active' : '' },
          { n: 4, label: 'Examen', sub: 'Présenter la convocation', cls: '' },
        ].map(s => (
          <div key={s.n} className={`step-item ${s.cls}`}>
            <div className="step-num">{s.cls === 'done' ? '✓' : s.n}</div>
            <div className="step-body"><strong>{s.label}</strong><span>{s.sub}</span></div>
          </div>
        ))}
      </div>

      <div className="g2">
        {/* Paiement Mobile Money */}
        <div className="card">
          <div className="card-header"><span className="card-title">Paiement</span></div>
          <div className="alert aw" style={{ marginBottom: 14 }}>
            <strong>Phase pilote</strong> — Le paiement s'effectue en espèces auprès de l'agent DNTT du centre.
            Mobile Money sera activé pour le déploiement national.
          </div>
          {!canAct && (
            <div className="alert ai" style={{ marginBottom: 14 }}>
              Connectez-vous avec un compte candidat pour effectuer un paiement réel.
            </div>
          )}
          <form onSubmit={handlePay} style={{ display: 'grid', gap: 14 }}>
            <label>
              Référence de réservation
              <input value={bookRef} onChange={e => setBookRef(e.target.value)} placeholder="GN-CONV-2026-000001" />
            </label>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink2)', marginBottom: 8 }}>Opérateur</div>
              <div className="providers">
                {[
                  { id: 'orange_money', icon: 'OM', label: 'Orange Money' },
                  { id: 'mtn_money',    icon: 'MTN', label: 'MTN Money' },
                  { id: 'wave',         icon: 'W', label: 'Wave' },
                  { id: 'paydunya',     icon: '', label: 'PayDunya' },
                ].map(p => (
                  <button type="button" key={p.id} className={`prov-btn${provider === p.id ? ' sel' : ''}`}
                    onClick={() => setProvider(p.id)}>
                    <div className="prov-icon">{p.icon}</div>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{p.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <label>Numéro de téléphone<input value={phone} onChange={e => setPhone(e.target.value)} placeholder="+224 6XX XXX XXX" /></label>
            <div style={{ background: 'var(--bg)', borderRadius: 'var(--r)', padding: '12px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: 'var(--muted)' }}>Montant</span>
              <strong style={{ fontSize: 18, fontWeight: 800 }}>{fmtGNF(amount)}</strong>
            </div>
            {payErr && <p className="form-error">{payErr}</p>}
            {payResult && (
              <div className="alert as">
                 Paiement <strong>{payResult.status === 'paid' ? 'confirmé' : payResult.status}</strong> — Réf. {payResult.reference}
                {payResult.checkout_url && (
                  <span> — <a href={payResult.checkout_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--blue-dark, #004085)', fontWeight: 600 }}>Finaliser Wave →</a></span>
                )}
              </div>
            )}
            <button type="submit" className="btn-success btn-block" disabled={paying}>
              {paying ? 'Traitement…' : `Payer ${fmtGNF(amount)}`}
            </button>
          </form>
        </div>

        {/* Convocation */}
        <div className="card">
          <div className="card-header"><span className="card-title"> Convocation & Documents</span></div>
          <div style={{ display: 'grid', gap: 12 }}>
            <label>
              Référence de réservation
              <input value={bookRef} onChange={e => setBookRef(e.target.value)} placeholder="GN-CONV-2026-000001" />
            </label>
            <button className="btn-primary btn-block" disabled={!bookRef}
              onClick={() => { if (bookRef) window.open(getConvocationPdfUrl(bookRef), '_blank', 'noopener'); }}>
              ↓ Télécharger la convocation PDF
            </button>
            <div className="divider" />
            <button className="btn-success btn-block" onClick={() => { window.location.hash = '#/exam'; }}>
              Accéder à l'examen →
            </button>
            <button className="secondary-button btn-block" onClick={() => { window.location.hash = '#/results'; }}>
              Voir mes résultats →
            </button>
          </div>
        </div>

        {/* Vérification certificat */}
        <div className="card">
          <div className="card-header"><span className="card-title">Vérifier un certificat</span></div>
          <form onSubmit={handleVerify} style={{ display: 'grid', gap: 12 }}>
            <label>
              Identifiant de tentative
              <input value={certId} onChange={e => setCertId(e.target.value)} placeholder="ATT-xxxxxxxx-xxxx-…" />
            </label>
            {certErr && <p className="form-error">{certErr}</p>}
            {cert && (
              <div className={`alert ${cert.valid && cert.passed ? 'as' : cert.valid ? 'aw' : 'ae'}`}>
                {cert.valid && cert.passed ? 'ADMIS' : cert.valid ? ' Ajourné' : ' Invalide'}{' '}
                — {cert.candidate_name ?? ''} {cert.score !== undefined ? `· ${cert.score}/40` : ''}
                {cert.valid && cert.passed && (
                  <button type="button" className="btn-sm" style={{ marginLeft: 10 }}
                    onClick={() => { window.open(getExamCertificatePdfUrl(certId), '_blank', 'noopener'); }}>
                    ↓ PDF
                  </button>
                )}
              </div>
            )}
            <button type="submit" className="secondary-button" disabled={checking || !certId.trim()}>
              {checking ? 'Vérification…' : 'Vérifier'}
            </button>
          </form>
        </div>

        {/* Infos pratiques */}
        <div className="card">
          <div className="card-header"><span className="card-title">Infos pratiques</span></div>
          <ul style={{ paddingLeft: 18, display: 'grid', gap: 8, fontSize: 13, color: 'var(--ink2)' }}>
            <li>Présentez-vous <strong>30 minutes avant</strong> la session</li>
            <li>Apportez votre <strong>pièce d'identité originale</strong></li>
            <li>Présentez la convocation PDF (QR code) à l'entrée</li>
            <li>Seuil d'admission : <strong>35/40</strong> (87,5 %)</li>
            <li>Durée : <strong>30 minutes</strong> — 40 questions tirées aléatoirement</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// CENTER PAGE — Espace centre d'examen
// ══════════════════════════════════════════════════════════════════
