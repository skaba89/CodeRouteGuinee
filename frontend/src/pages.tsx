import { type FormEvent, useEffect, useRef, useCallback, useState } from 'react';
import { AudioModeBanner, LocaleAudioSwitcher, PlayButton, AudioToggle } from './components/AudioButton';
import { isAudioLocale, speakFeedback, stop as stopAudio } from './audio';
import { type Locale } from './i18n';
import { type AuthUser } from './authClient';
import { type UserRole } from './auth';
import { useAuthSession, canUseProtectedActions } from './authSession';
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
} from './api';
import { DEMO_QUESTIONS } from './pages/examQuestions';

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
              <div className="actions">
                <button className="btn-sm secondary-button" onClick={() => downloadDashboardCsv().catch(() => undefined)}>⬇ Export dashboard</button>
                <button className="btn-sm secondary-button" onClick={() => downloadAuditLogsCsv().catch(() => undefined)}>⬇ Export audit</button>
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
            <div>⏱ 30 minutes • 40 questions officielles</div>
            <div>✅ Seuil d'admission : 35/40 (87,5 %)</div>
            <div>📱 Questions illustrées par catégorie</div>
          </div>
          <a href="#/exam"><button className="btn-success">Passer l'examen →</button></a>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// CANDIDATE PAGE — Espace candidat complet
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
          <div className="card-header"><span className="card-title">💳 Paiement Mobile Money</span></div>
          {!canAct && (
            <div className="alert ai" style={{ marginBottom: 14 }}>
              ℹ️ Connectez-vous avec un compte candidat pour effectuer un paiement réel.
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
                  { id: 'orange_money', icon: '🟠', label: 'Orange Money' },
                  { id: 'mtn_money',    icon: '🟡', label: 'MTN Money' },
                  { id: 'wave',         icon: '🔵', label: 'Wave' },
                  { id: 'paydunya',     icon: '💳', label: 'PayDunya' },
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
                ✅ Paiement <strong>{payResult.status === 'paid' ? 'confirmé' : payResult.status}</strong> — Réf. {payResult.reference}
              </div>
            )}
            <button type="submit" className="btn-success btn-block" disabled={paying}>
              {paying ? 'Traitement…' : `Payer ${fmtGNF(amount)}`}
            </button>
          </form>
        </div>

        {/* Convocation */}
        <div className="card">
          <div className="card-header"><span className="card-title">📄 Convocation & Documents</span></div>
          <div style={{ display: 'grid', gap: 12 }}>
            <label>
              Référence de réservation
              <input value={bookRef} onChange={e => setBookRef(e.target.value)} placeholder="GN-CONV-2026-000001" />
            </label>
            <a href={bookRef ? getConvocationPdfUrl(bookRef) : '#'} target="_blank" rel="noreferrer">
              <button className="btn-primary btn-block" disabled={!bookRef}>
                ⬇ Télécharger la convocation PDF
              </button>
            </a>
            <div className="divider" />
            <a href="#/exam">
              <button className="btn-success btn-block">🎓 Accéder à l'examen →</button>
            </a>
            <a href="#/results">
              <button className="secondary-button btn-block">📊 Voir mes résultats →</button>
            </a>
          </div>
        </div>

        {/* Vérification certificat */}
        <div className="card">
          <div className="card-header"><span className="card-title">🏆 Vérifier un certificat</span></div>
          <form onSubmit={handleVerify} style={{ display: 'grid', gap: 12 }}>
            <label>
              Identifiant de tentative
              <input value={certId} onChange={e => setCertId(e.target.value)} placeholder="ATT-xxxxxxxx-xxxx-…" />
            </label>
            {certErr && <p className="form-error">{certErr}</p>}
            {cert && (
              <div className={`alert ${cert.valid && cert.passed ? 'as' : cert.valid ? 'aw' : 'ae'}`}>
                {cert.valid && cert.passed ? '🏆 ADMIS' : cert.valid ? '📋 Ajourné' : '❌ Invalide'}{' '}
                — {cert.candidate_name ?? ''} {cert.score !== undefined ? `· ${cert.score}/40` : ''}
                {cert.valid && cert.passed && (
                  <button type="button" className="btn-sm" style={{ marginLeft: 10 }}
                    onClick={() => downloadExamCertificatePdf(certId).catch(() => undefined)}>
                    ⬇ PDF
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
          <div className="card-header"><span className="card-title">ℹ️ Infos pratiques</span></div>
          <ul style={{ paddingLeft: 18, display: 'grid', gap: 8, fontSize: 13, color: 'var(--ink2)' }}>
            <li>Présentez-vous <strong>30 minutes avant</strong> la session</li>
            <li>Apportez votre <strong>pièce d'identité originale</strong></li>
            <li>Présentez la convocation PDF (QR code) à l'entrée</li>
            <li>Seuil d'admission : <strong>35/40</strong> (87,5 %)</li>
            <li>Durée : <strong>30 minutes</strong> — 40 questions</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// CENTER PAGE — Espace centre d'examen
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
    getCenters().then(setCenters).catch(() => undefined);
    getCenterIncidents('open', 10).then(setIncidents).catch(() => undefined);
  }, []);

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
      getCenterIncidents('open', 10).then(setIncidents).catch(() => undefined);
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
          ⚠️ Connectez-vous avec un compte <strong>center</strong> pour utiliser les fonctionnalités réelles.
        </div>
      )}

      <div className="g2">
        {/* Validation entrée */}
        <div className="card">
          <div className="card-header"><span className="card-title">🔍 Valider l'entrée candidat</span></div>
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
                <div className="scanner-icon">{entryResult.allowed ? '✅' : '❌'}</div>
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
          <div className="card-header"><span className="card-title">🚀 Démarrer un examen</span></div>
          <form onSubmit={handleStartExam} style={{ display: 'grid', gap: 12 }}>
            <label>Référence de réservation<input value={bookingRef} onChange={e => setBookingRef(e.target.value)} placeholder="GN-CONV-2026-000001" /></label>
            <label>Code du poste<input value={deviceKey} onChange={e => setDeviceKey(e.target.value)} placeholder="POSTE-01" /></label>
            {startErr && <p className="form-error">{startErr}</p>}
            {attempt && (
              <div className="alert as">
                ✅ Examen démarré — ID : <code style={{ fontSize: 11 }}>{attempt.id}</code>
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
          <div className="card-header"><span className="card-title">⚠️ Déclarer un incident</span></div>
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
            <span className="card-title">📋 Incidents ouverts ({incidents.length})</span>
            <button className="btn-sm secondary-button" onClick={() => getCenterIncidents('open', 10).then(setIncidents).catch(() => undefined)}>
              Actualiser
            </button>
          </div>
          {incidents.length === 0 ? (
            <div className="empty-state"><p>Aucun incident en cours ✅</p></div>
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
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// ADMIN PAGE — Tableau de bord administration
// ══════════════════════════════════════════════════════════════════
export function AdminPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAdmin = canUseProtectedActions(currentUser, isPresentationMode, ['admin','super_admin']);
  const canSA = canUseProtectedActions(currentUser, isPresentationMode, ['super_admin']);

  const [tab, setTab] = useState<'dashboard'|'candidates'|'payments'|'monitoring'|'questions'|'audit'|'users'>('dashboard');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [examSum, setExamSum] = useState<ExamSummary | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [users, setUsers] = useState<InstitutionalUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // Création utilisateur
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('admin');
  const [newPass, setNewPass] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => undefined);
    getExamSummary().then(setExamSum).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (tab === 'candidates') getCandidates().then(setCandidates).catch(() => undefined);
    if (tab === 'audit') getAuditLogs().then(setAuditLogs).catch(() => undefined);
    if (tab === 'users') getInstitutionalUsers().then(setUsers).catch(() => undefined);
  }, [tab]);

  async function handleCreateUser(e: FormEvent) {
    e.preventDefault();
    setCreating(true); setMsg(null);
    try {
      await createInstitutionalUser({ email: newEmail, full_name: newName, role: newRole, initial_password: newPass, reason: 'Création par super_admin' });
      setMsg('✅ Utilisateur créé.');
      setNewEmail(''); setNewName(''); setNewPass('');
      getInstitutionalUsers().then(setUsers).catch(() => undefined);
    } catch (err) {
      setMsg('❌ ' + errMsg(err, 'Création échouée.'));
    } finally { setCreating(false); }
  }

  const TABS = [
    { id: 'dashboard',  label: '📊 Dashboard' },
    { id: 'candidates', label: '👥 Candidats' },
    { id: 'payments',   label: '💳 Paiements' },
    { id: 'monitoring', label: '🔍 Monitoring' },
    { id: 'questions',  label: '📝 Questions' },
    { id: 'audit',      label: '📋 Audit' },
    { id: 'users',      label: '👤 Utilisateurs' },
  ] as const;

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Administration</span>
        <h1>Tableau de bord national</h1>
        <p>Vue d'ensemble et gestion de la plateforme CodeRoute Guinée.</p>
      </div>

      {!canAdmin && (
        <div className="alert aw">⚠️ Connectez-vous avec un compte admin ou super_admin pour accéder aux données réelles.</div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} type="button"
            className={tab === t.id ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
            onClick={() => setTab(t.id as typeof tab)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Dashboard tab */}
      {tab === 'dashboard' && (
        <>
          {dashboard && (
            <div className="stats-grid">
              <div className="stat-card s-blue"><div className="stat-label">Candidats</div><div className="stat-value">{fmt(dashboard.candidates)}</div></div>
              <div className="stat-card s-green"><div className="stat-label">Centres agréés</div><div className="stat-value">{fmt(dashboard.accredited_centers)}</div></div>
              <div className="stat-card s-gold"><div className="stat-label">Sessions</div><div className="stat-value">{fmt(dashboard.exam_sessions)}</div></div>
              <div className="stat-card s-red"><div className="stat-label">Alertes fraude</div><div className="stat-value">{fmt(dashboard.fraud_alerts)}</div></div>
            </div>
          )}
          {examSum && (
            <div className="g2">
              <div className="card">
                <div className="card-header"><span className="card-title">🎓 Examens</span></div>
                <div className="stats-grid" style={{ marginBottom: 0 }}>
                  <div><div className="stat-label">Total</div><div className="stat-value">{fmt(examSum.total_attempts)}</div></div>
                  <div><div className="stat-label">Admis</div><div className="stat-value" style={{ color: 'var(--green)' }}>{fmt(examSum.passed_attempts)}</div></div>
                  <div><div className="stat-label">Ajournés</div><div className="stat-value" style={{ color: 'var(--red)' }}>{fmt(examSum.failed_attempts)}</div></div>
                  <div><div className="stat-label">Score moy.</div><div className="stat-value">{examSum.average_score}<span style={{ fontSize: 14, fontWeight: 500 }}>/40</span></div></div>
                </div>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">⚡ Exports</span></div>
                <div className="actions">
                  <button className="secondary-button btn-sm" onClick={() => downloadDashboardCsv().catch(() => undefined)}>⬇ Dashboard CSV</button>
                  <button className="secondary-button btn-sm" onClick={() => downloadAuditLogsCsv().catch(() => undefined)}>⬇ Audit CSV</button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Candidats tab */}
      {tab === 'candidates' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">👥 Candidats ({candidates.length})</span>
            <button className="secondary-button btn-sm" onClick={() => getCandidates().then(setCandidates).catch(() => undefined)}>Actualiser</button>
          </div>
          {candidates.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--muted)' }}>
              {canAdmin ? 'Chargement…' : 'Connectez-vous pour voir les candidats.'}
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Référence</th><th>Nom</th><th>Prénom</th><th>Téléphone</th><th>Catégorie</th><th>Statut</th></tr></thead>
                <tbody>
                  {candidates.slice(0, 50).map(c => (
                    <tr key={c.id}>
                      <td><code style={{ fontSize: 11 }}>{c.reference}</code></td>
                      <td>{c.last_name}</td>
                      <td>{c.first_name}</td>
                      <td>{c.phone}</td>
                      <td><span className="badge bb">Cat. {c.permit_category}</span></td>
                      <td><span className={`badge ${c.status === 'active' ? 'bg' : 'bgr'}`}>{c.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Paiements tab */}
      {tab === 'payments' && <PaymentsPanel canAdmin={canAdmin} />}

      {/* Audit logs tab */}
      {tab === 'audit' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📋 Audit logs ({auditLogs.length})</span>
            <button className="secondary-button btn-sm" onClick={() => downloadAuditLogsCsv().catch(() => undefined)}>⬇ CSV</button>
          </div>
          {auditLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
              {canAdmin ? 'Aucun log trouvé.' : 'Connectez-vous pour voir les logs.'}
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Action</th><th>Entité</th><th>Détails</th></tr></thead>
                <tbody>
                  {auditLogs.slice(0, 100).map((log, i) => (
                    <tr key={i}>
                      <td style={{ whiteSpace: 'nowrap' }}>{fmtDate(log.created_at)}</td>
                      <td><code style={{ fontSize: 11 }}>{log.action}</code></td>
                      <td>{log.entity}</td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11 }}>
                        {JSON.stringify(log.details).slice(0, 80)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Monitoring tab */}
      {tab === 'monitoring' && <MonitoringPanel canAdmin={canAdmin} />}

      {/* Questions tab */}
      {tab === 'questions' && <QuestionsPanel canAdmin={canAdmin} />}

      {/* Users tab */}
      {tab === 'users' && (
        <div className="g2">
          {canSA && (
            <div className="card">
              <div className="card-header"><span className="card-title">➕ Créer un utilisateur</span></div>
              <form onSubmit={handleCreateUser} style={{ display: 'grid', gap: 12 }}>
                <label>Nom complet<input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Prénom Nom" /></label>
                <label>Email<input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} placeholder="agent@coderoute.gov.gn" /></label>
                <label>
                  Rôle
                  <select value={newRole} onChange={e => setNewRole(e.target.value)}>
                    <option value="admin">Admin national</option>
                    <option value="center">Chef de centre</option>
                  </select>
                </label>
                <label>Mot de passe temporaire<input type="password" value={newPass} onChange={e => setNewPass(e.target.value)} placeholder="12 caractères minimum" /></label>
                {msg && <p className={msg.startsWith('✅') ? 'login-status' : 'form-error'}>{msg}</p>}
                <button type="submit" className="btn-primary" disabled={creating || !newEmail || !newName || newPass.length < 12}>
                  {creating ? 'Création…' : 'Créer l\'utilisateur'}
                </button>
              </form>
            </div>
          )}
          <div className="card">
            <div className="card-header">
              <span className="card-title">👤 Comptes ({users.length})</span>
              <button className="secondary-button btn-sm" onClick={() => getInstitutionalUsers().then(setUsers).catch(() => undefined)}>Actualiser</button>
            </div>
            {users.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                {canAdmin ? 'Aucun utilisateur.' : 'Connectez-vous.'}
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Statut</th></tr></thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id}>
                        <td>{u.full_name}</td>
                        <td style={{ fontSize: 12 }}>{u.email}</td>
                        <td><span className="badge bb">{u.role}</span></td>
                        <td><span className={`badge ${u.is_active ? 'bg' : 'bgr'}`}>{u.is_active ? 'Actif' : 'Inactif'}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ── Monitoring sub-panel ───────────────────────────────────────────
function MonitoringPanel({ canAdmin }: { canAdmin: boolean }) {
  const [summaries, setSummaries] = useState<ExamMonitoringSummary[]>([]);
  const [events, setEvents] = useState<ExamMonitoringEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    Promise.allSettled([
      getExamMonitoringSummaries({ limit: 20 }),
      getExamMonitoringEvents({ limit: 30 }),
    ]).then(([s, e]) => {
      if (s.status === 'fulfilled') setSummaries(s.value);
      if (e.status === 'fulfilled') setEvents(e.value);
    }).finally(() => setLoading(false));
  }, [canAdmin]);

  if (!canAdmin) return <div className="alert aw">⚠️ Accès réservé aux administrateurs.</div>;

  return (
    <div className="g2">
      <div className="card">
        <div className="card-header">
          <span className="card-title">🔍 Résumés de monitoring ({summaries.length})</span>
          <button className="secondary-button btn-sm" aria-label="Actualiser le monitoring" onClick={() => getExamMonitoringSummaries({ limit: 20 }).then(setSummaries).catch(() => undefined)}>Actualiser</button>
        </div>
        {loading ? <p className="text-muted" style={{ padding: 16 }}>Chargement…</p> :
          summaries.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Aucune anomalie détectée ✅</div> :
          <div className="table-wrap">
            <table>
              <thead><tr><th>Tentative</th><th>Risque</th><th>Anomalies</th><th>Statut</th></tr></thead>
              <tbody>
                {summaries.map((s, i) => (
                  <tr key={i}>
                    <td><code style={{ fontSize: 11 }}>{s.attempt_id?.slice(0,16)}…</code></td>
                    <td>
                      <span className={`badge ${((s as Record<string,unknown>)["max_risk_score"] as number ?? 0) > 70 ? 'br' : ((s as Record<string,unknown>)["max_risk_score"] as number ?? 0) > 40 ? 'bgo' : 'bg'}`}>
                        {((s as Record<string,unknown>)["max_risk_score"] as number) ?? 0}
                      </span>
                    </td>
                    <td>{((s as Record<string,unknown>)["anomaly_count"] as number) ?? 0}</td>
                    <td><span className="badge bgr">{((s as Record<string,unknown>)['review_status'] as string) ?? 'pending'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        }
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">⚡ Événements récents ({events.length})</span>
          <button className="secondary-button btn-sm" aria-label="Télécharger export CSV" onClick={() => downloadExamAttemptsCsv().catch(() => undefined)}>⬇ Export</button>
        </div>
        {loading ? <p className="text-muted" style={{ padding: 16 }}>Chargement…</p> :
          events.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Aucun événement récent</div> :
          <div className="table-wrap">
            <table>
              <thead><tr><th>Événement</th><th>Score</th><th>Date</th></tr></thead>
              <tbody>
                {events.slice(0, 20).map((e, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 12 }}>{e.event_type}</td>
                    <td>
                      <span className={`badge ${(e.risk_score ?? 0) > 70 ? 'br' : (e.risk_score ?? 0) > 40 ? 'bgo' : 'bgr'}`}>
                        {e.risk_score ?? 0}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {e.created_at ? fmtDate(e.created_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        }
      </div>
    </div>
  );
}

// ── Questions sub-panel ─────────────────────────────────────────────
function QuestionsPanel({ canAdmin }: { canAdmin: boolean }) {
  const [items, setItems] = useState<QuestionGovernanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState<string | null>(null);

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    getQuestionGovernanceItems().then(setItems).catch(() => undefined).finally(() => setLoading(false));
  }, [canAdmin]);

  async function handleDecide(questionId: string, status: 'approved' | 'rejected', reason: string) {
    setDeciding(questionId);
    try {
      await decideQuestionGovernance(questionId, status, reason);
      getQuestionGovernanceItems().then(setItems).catch(() => undefined);
    } catch { /* silencieux */ }
    finally { setDeciding(null); }
  }

  if (!canAdmin) return <div className="alert aw">⚠️ Accès réservé aux administrateurs.</div>;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">📝 Gouvernance des questions ({items.length})</span>
        <button className="secondary-button btn-sm" onClick={() => getQuestionGovernanceItems().then(setItems).catch(() => undefined)}>Actualiser</button>
      </div>
      {loading ? <p className="text-muted" style={{ padding: 16 }}>Chargement…</p> :
        items.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Toutes les questions sont validées ✅</div> :
        <div className="table-wrap">
          <table>
            <thead><tr><th>Catégorie</th><th>Question</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody>
              {items.map(item => (
                <tr key={item.question_id}>
                  <td><span className="badge bb">{item.category}</span></td>
                  <td style={{ maxWidth: 300, fontSize: 13 }}>
                    {(item.text ?? '').slice(0, 80)}{(item.text ?? '').length > 80 ? '…' : ''}
                  </td>
                  <td>
                    <span className={`badge ${item.latest_status === 'approved' ? 'bg' : item.latest_status === 'rejected' ? 'br' : 'bgo'}`}>
                      {item.latest_status ?? 'pending'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn-sm btn-success"
                        disabled={deciding === item.question_id || item.latest_status === 'approved'}
                        onClick={() => handleDecide(item.question_id, 'approved', 'Validée par admin')}>
                        ✅
                      </button>
                      <button className="btn-sm btn-danger"
                        disabled={deciding === item.question_id || item.latest_status === 'rejected'}
                        onClick={() => handleDecide(item.question_id, 'rejected', 'Rejetée par admin')}>
                        ❌
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      }
    </div>
  );
}

// ── Payments sub-panel ────────────────────────────────────────────
function PaymentsPanel({ canAdmin }: { canAdmin: boolean }) {
  const [items, setItems] = useState<import('./api').PaymentReconciliationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPaymentReconciliationItems({}).then(setItems).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="card-header"><span className="card-title">💳 Paiements</span></div>
      {loading ? (
        <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>Chargement…</div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
          {canAdmin ? 'Aucun paiement trouvé.' : 'Connectez-vous pour voir les paiements.'}
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Référence</th><th>Réservation</th><th>Montant</th><th>Provider</th><th>Statut</th></tr></thead>
            <tbody>
              {items.slice(0, 50).map(p => (
                <tr key={p.reference}>
                  <td><code style={{ fontSize: 11 }}>{p.reference}</code></td>
                  <td style={{ fontSize: 12 }}>{p.booking_reference}</td>
                  <td>{fmtGNF(p.amount_gnf)}</td>
                  <td>{p.provider}</td>
                  <td><span className={`badge ${p.status === 'paid' ? 'bg' : p.status === 'pending' ? 'bgo' : 'br'}`}>{p.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// INSTITUTIONAL DOSSIER PAGE
// ══════════════════════════════════════════════════════════════════
export function InstitutionalDossierPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAdmin = canUseProtectedActions(currentUser, isPresentationMode, ['admin','super_admin']);
  const [identityChecks, setIdentityChecks] = useState<CandidateIdentityCheck[]>([]);
  const [submissions, setSubmissions] = useState<CandidateSubmission[]>([]);

  useEffect(() => {
    if (!canAdmin) return;
    getCandidateIdentityChecks({ status_filter: 'pending', limit: 25 }).then(setIdentityChecks).catch(() => undefined);
    getCandidateSubmissions({ status_filter: 'submitted', limit: 25 }).then(setSubmissions).catch(() => undefined);
  }, [canAdmin]);

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Institutionnel</span>
        <h1>Dossier d'État</h1>
        <p>Pilotage national — vérifications d'identité, recours et habilitations.</p>
      </div>

      {!canAdmin && (
        <div className="alert aw">⚠️ Réservé aux administrateurs nationaux.</div>
      )}

      <div className="g2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">🪪 Vérifications d'identité ({identityChecks.length})</span>
            <button className="secondary-button btn-sm" onClick={() => getCandidateIdentityChecks({ status_filter: 'pending', limit: 25 }).then(setIdentityChecks).catch(() => undefined)}>Actualiser</button>
          </div>
          {identityChecks.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>{canAdmin ? 'Aucune vérification en attente ✅' : 'Connectez-vous.'}</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Candidat</th><th>Document</th><th>Référence</th><th>Statut</th><th>Actions</th></tr></thead>
                <tbody>
                  {identityChecks.map(c => (
                    <tr key={c.id}>
                      <td style={{ fontSize: 12 }}>{c.candidate_id}</td>
                      <td>{c.document_type}</td>
                      <td style={{ fontSize: 11 }}>{c.document_reference}</td>
                      <td><span className={`badge ${c.status === 'approved' ? 'bg' : c.status === 'pending' ? 'bgo' : 'br'}`}>{c.status}</span></td>
                      <td>
                        {c.status === 'pending' && canAdmin && (
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button className="btn-sm btn-success" onClick={() => decideCandidateIdentity(c.id, 'approved', 'Validé').then(() => getCandidateIdentityChecks({ status_filter: 'pending', limit: 25 }).then(setIdentityChecks).catch(() => undefined)).catch(() => undefined)}>✅</button>
                            <button className="btn-sm btn-danger" onClick={() => decideCandidateIdentity(c.id, 'rejected', 'Rejeté').then(() => getCandidateIdentityChecks({ status_filter: 'pending', limit: 25 }).then(setIdentityChecks).catch(() => undefined)).catch(() => undefined)}>❌</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">📩 Recours candidats ({submissions.length})</span>
            <button className="secondary-button btn-sm" onClick={() => getCandidateSubmissions({ status_filter: 'submitted', limit: 25 }).then(setSubmissions).catch(() => undefined)}>Actualiser</button>
          </div>
          {submissions.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>{canAdmin ? 'Aucun recours en attente ✅' : 'Connectez-vous.'}</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Candidat</th><th>Catégorie</th><th>Message</th><th>Statut</th><th>Actions</th></tr></thead>
                <tbody>
                  {submissions.map(s => (
                    <tr key={s.id}>
                      <td style={{ fontSize: 12 }}>{s.candidate_id}</td>
                      <td><span className="badge bb">{s.category}</span></td>
                      <td style={{ maxWidth: 200, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.message}</td>
                      <td><span className={`badge ${s.status === 'approved' ? 'bg' : s.status === 'submitted' ? 'bgo' : 'br'}`}>{s.status}</span></td>
                      <td>
                        {s.status === 'submitted' && canAdmin && (
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button className="btn-sm btn-success" onClick={() => handleCandidateSubmission(s.id, 'approved', 'Accepté').then(() => getCandidateSubmissions({ status_filter: 'submitted', limit: 25 }).then(setSubmissions).catch(() => undefined)).catch(() => undefined)}>✅</button>
                            <button className="btn-sm btn-danger" onClick={() => handleCandidateSubmission(s.id, 'rejected', 'Rejeté').then(() => getCandidateSubmissions({ status_filter: 'submitted', limit: 25 }).then(setSubmissions).catch(() => undefined)).catch(() => undefined)}>❌</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">📊 Pilotage national</span></div>
          <div style={{ display: 'grid', gap: 10 }}>
            <a href="#/admin"><button className="secondary-button btn-block">→ Tableau de bord admin</button></a>
            <button className="secondary-button btn-block" onClick={() => downloadInstitutionalReportPdf().catch(() => undefined)}>⬇ Rapport institutionnel PDF</button>
            <button className="secondary-button btn-block" onClick={() => downloadDashboardCsv().catch(() => undefined)}>⬇ Export dashboard CSV</button>
            <button className="secondary-button btn-block" onClick={() => downloadAuditLogsCsv().catch(() => undefined)}>⬇ Export audit complet</button>
            <button className="secondary-button btn-block" onClick={() => downloadExamAttemptsCsv().catch(() => undefined)}>⬇ Export examens CSV</button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// EXAM PAGE — Interface d'examen complète avec SVG
// ══════════════════════════════════════════════════════════════════

// ── SVG Signs ─────────────────────────────────────────────────────
function SignSvg({ type }: { type: string }) {
  if (type === 'stop') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <polygon points="60,5 105,28 115,75 90,112 30,112 5,75 15,28" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
      <text x="60" y="68" textAnchor="middle" fill="#fff" fontSize="20" fontWeight="bold">STOP</text>
    </svg>
  );
  if (type === 'give_way') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <polygon points="60,115 5,15 115,15" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
      <polygon points="60,100 18,28 102,28" fill="#fff" stroke="#c0392b" strokeWidth="4"/>
    </svg>
  );
  if (type === 'speed_50') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <text x="60" y="74" textAnchor="middle" fill="#0A2540" fontSize="32" fontWeight="bold">50</text>
    </svg>
  );
  if (type === 'no_entry') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
      <rect x="20" y="50" width="80" height="20" rx="4" fill="#fff"/>
    </svg>
  );
  if (type === 'roundabout') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
      <circle cx="60" cy="60" r="22" fill="none" stroke="#fff" strokeWidth="5"/>
      <path d="M38 60 Q38 38 60 38" fill="none" stroke="#fff" strokeWidth="5"/>
      <polygon points="60,35 55,45 65,45" fill="#fff"/>
    </svg>
  );
  if (type === 'mandatory') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
      <path d="M30 60 L90 60 M75 45 L90 60 L75 75" stroke="#fff" strokeWidth="8" fill="none" strokeLinecap="round"/>
    </svg>
  );
  return <svg viewBox="0 0 120 120" width="110" height="110"><circle cx="60" cy="60" r="55" fill="#e2e8f0"/><text x="60" y="68" textAnchor="middle" fontSize="12" fill="#667085">Illustration</text></svg>;
}

function SceneSvg({ type }: { type: string }) {
  if (type === 'intersection') return (
    <svg viewBox="0 0 200 200" width="100%" style={{ maxWidth: 300, display: 'block', margin: '0 auto' }}>
      <rect x="0" y="85" width="200" height="30" fill="#555"/>
      <rect x="85" y="0" width="30" height="200" fill="#555"/>
      <line x1="0" y1="100" x2="80" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <line x1="120" y1="100" x2="200" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <line x1="100" y1="0" x2="100" y2="80" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <line x1="100" y1="120" x2="100" y2="200" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <rect x="18" y="90" width="36" height="18" rx="4" fill="#3498db"/>
      <text x="36" y="103" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">A →</text>
      <rect x="90" y="148" width="20" height="34" rx="4" fill="#e74c3c"/>
      <text x="100" y="168" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">B ↑</text>
      <text x="100" y="193" textAnchor="middle" fill="#f1c40f" fontSize="9" fontWeight="bold">B est prioritaire</text>
    </svg>
  );
  if (type === 'safe_distance') return (
    <svg viewBox="0 0 300 120" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }}>
      <rect width="300" height="120" fill="#1a2e1a"/>
      <rect x="0" y="50" width="300" height="50" fill="#3d3d3d"/>
      <line x1="0" y1="75" x2="300" y2="75" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <rect x="10" y="55" width="56" height="28" rx="5" fill="#3498db"/>
      <text x="38" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
      <rect x="180" y="55" width="56" height="28" rx="5" fill="#e74c3c"/>
      <text x="208" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">DEVANT</text>
      <line x1="68" y1="80" x2="178" y2="80" stroke="#27ae60" strokeWidth="2"/>
      <text x="123" y="100" textAnchor="middle" fill="#27ae60" fontSize="11" fontWeight="bold">≥ 2 secondes</text>
    </svg>
  );
  if (type === 'emergency') return (
    <svg viewBox="0 0 280 130" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }}>
      <rect width="280" height="130" fill="#0d1117"/>
      <rect x="0" y="55" width="280" height="50" fill="#3d3d3d"/>
      <line x1="0" y1="80" x2="280" y2="80" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <rect x="20" y="84" width="44" height="18" rx="4" fill="#3498db" opacity="0.7"/>
      <rect x="210" y="84" width="44" height="18" rx="4" fill="#2ecc71" opacity="0.7"/>
      <rect x="108" y="60" width="64" height="28" rx="5" fill="#fff"/>
      <text x="140" y="78" textAnchor="middle" fill="#c0392b" fontSize="11" fontWeight="bold">🚑 SAMU</text>
      <circle cx="140" cy="58" r="6" fill="#c0392b"/>
      <text x="140" y="120" textAnchor="middle" fill="#f1c40f" fontSize="10" fontWeight="bold">Dégagez la voie — priorité absolue</text>
    </svg>
  );
  if (type === 'overtake') return (
    <svg viewBox="0 0 280 150" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }}>
      <rect width="280" height="150" fill="#1a2e1a"/>
      <rect x="0" y="65" width="280" height="55" fill="#3d3d3d"/>
      <rect x="0" y="93" width="280" height="3" fill="#fff"/>
      <path d="M0 125 Q140 35 280 125" stroke="#3d3d3d" strokeWidth="55" fill="none"/>
      <rect x="36" y="70" width="46" height="21" rx="5" fill="#3498db"/>
      <rect x="100" y="70" width="46" height="21" rx="5" fill="#e74c3c"/>
      <text x="59" y="85" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
      <text x="123" y="85" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">CAMION</text>
      <circle cx="200" cy="36" r="18" fill="rgba(192,57,43,0.9)"/>
      <text x="200" y="41" textAnchor="middle" fill="#fff" fontSize="14" fontWeight="bold">✗</text>
    </svg>
  );
  return <div style={{ height: 120, background: '#f1f5f9', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13 }}>Illustration</div>;
}

type QData = { id: string; number: number; category: string; text: string; options: string[]; correct: string; media?: string; mediaType?: 'sign'|'scene'; expl: string; };

function Timer({ secs, total, onExpire }: { secs: number; total: number; onExpire: () => void }) {
  const [rem, setRem] = useState(secs);
  const fired = useRef(false);
  useEffect(() => {
    if (rem <= 0 && !fired.current) { fired.current = true; onExpire(); return; }
    const t = setTimeout(() => setRem(r => Math.max(0, r - 1)), 1000);
    return () => clearTimeout(t);
  }, [rem, onExpire]);
  const m = Math.floor(rem / 60), s = rem % 60;
  const pct = (rem / total * 100).toFixed(1) + '%';
  const urgent = rem <= 300, crit = rem <= 60;
  const color = crit ? '#D32F2F' : urgent ? '#F5A623' : '#00875A';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 90, height: 90, borderRadius: '50%', background: `conic-gradient(${color} ${pct}, #E4E7EC 0)`, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
        <div style={{ width: 72, height: 72, borderRadius: '50%', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 20, fontWeight: 900, fontVariantNumeric: 'tabular-nums', color: 'var(--ink)' }}>
            {String(m).padStart(2,'0')}:{String(s).padStart(2,'0')}
          </span>
        </div>
      </div>
      <p style={{ fontSize: 11, color: crit ? '#D32F2F' : 'var(--muted)', fontWeight: crit ? 700 : 500 }}>
        {crit ? '⚠️ Temps critique !' : urgent ? '⏳ < 5 min' : 'Temps restant'}
      </p>
    </div>
  );
}

function QGrid({ total, cur, ans, onSelect }: { total: number; cur: number; ans: Record<number,string>; onSelect: (i: number) => void }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8,1fr)', gap: 3 }}>
      {Array.from({ length: total }, (_, i) => (
        <button key={i} type="button" onClick={() => onSelect(i)}
          style={{
            aspectRatio: '1', borderRadius: 5, border: '1.5px solid',
            borderColor: i === cur ? 'var(--navy)' : ans[i] ? '#86efac' : 'var(--border)',
            background: i === cur ? 'var(--navy)' : ans[i] ? '#dcfce7' : 'var(--bg)',
            color: i === cur ? '#fff' : ans[i] ? '#166534' : 'var(--muted)',
            fontSize: 10, fontWeight: 700, cursor: 'pointer', padding: 0, minHeight: 'unset',
          }}>
          {i + 1}
        </button>
      ))}
    </div>
  );
}

export function ExamPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const isAuth = !isPresentationMode && currentUser !== null;
  const SECS = 30 * 60;

  const questions: QData[] = DEMO_QUESTIONS.map((q: import('./pages/examQuestions').ExamQuestionData) => ({
    id: q.id, number: q.number, category: q.category, text: q.text,
    options: q.options, correct: q.correct_answer,
    media: q.media_url ?? undefined,
    mediaType: q.media_url ? (q.media_url.startsWith('intersection') || q.media_url.startsWith('situation') ? 'scene' : 'sign') : undefined,
    expl: q.explanation ?? '',
  }));

  const [phase, setPhase] = useState<'setup'|'running'|'review'|'done'>('setup');
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number,string>>({});
  const [bookRef, setBookRef] = useState('');
  const [result, setResult] = useState<ExamDetailedResult | null>(null);
  const [filter, setFilter] = useState<'all'|'ok'|'ko'>('all');
  const [reveal, setReveal] = useState(false);

  const q = questions[idx];
  const answered = Object.keys(answers).length;
  const handleExpire = useCallback(() => setPhase('done'), []);

  function pick(opt: string) {
    setAnswers(a => ({ ...a, [idx]: opt }));
    if (!reveal) { setReveal(true); setTimeout(() => { setReveal(false); if (idx < questions.length - 1) setIdx(i => i + 1); }, 1200); }
  }

  async function submitExam() {
    // Calcul local pour la démo
    const score = questions.filter((q2, i) => answers[i] === q2.correct).length;
    const passed = score >= 35;
    const fakeResult: ExamDetailedResult = {
      attempt_id: 'DEMO',
      candidate_name: currentUser?.full_name ?? 'Candidat',
      score, total: questions.length,
      score_percent: Math.round(score / questions.length * 1000) / 10,
      passed, threshold: 35,
      submitted_at: new Date().toISOString(),
      questions: questions.map((q2, i) => ({
        number: q2.number, question_id: q2.id, category: q2.category,
        text: q2.text, options: q2.options,
        given_answer: answers[i] ?? null,
        correct_answer: q2.correct, is_correct: answers[i] === q2.correct,
        explanation: q2.expl,
      })),
    };
    setResult(fakeResult);
    setPhase('done');
  }

  // ── Setup ──────────────────────────────────────────────────────
  if (phase === 'setup') return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div style={{ maxWidth: 520, margin: '0 auto' }}>
        <AudioModeBanner />
        <div style={{ background: 'linear-gradient(135deg,var(--navy),var(--navy2))', borderRadius: 20, padding: 28, color: '#fff', marginBottom: 20, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>🇬🇳</div>
          <h2 style={{ color: '#fff', fontSize: 22 }}>Code de la route — Catégorie B</h2>
          <p style={{ color: 'rgba(255,255,255,.7)', marginTop: 6, fontSize: 13 }}>40 questions • 30 minutes • Seuil 35/40</p>
        </div>
        <div className="card">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
            {[['📋','40 questions illustrées'],['⏱','30 minutes'],['✅','Seuil : 35/40'],['🎯','Résultats détaillés']].map(([icon,label]) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: 'var(--bg)', borderRadius: 'var(--r)', fontSize: 13, fontWeight: 500 }}>
                <span>{icon}</span><span>{label}</span>
              </div>
            ))}
          </div>
          {isAuth && (
            <label style={{ marginBottom: 14 }}>
              Référence de réservation (optionnel)
              <input value={bookRef} onChange={e => setBookRef(e.target.value)} placeholder="GN-CONV-2026-000001" />
            </label>
          )}
          <button className="btn-success btn-block btn-lg" onClick={() => setPhase('running')}>
            🚀 {isAuth ? 'Démarrer l\'examen officiel' : 'Commencer la démonstration'}
          </button>
        </div>
      </div>
    </section>
  );

  // ── Done / Results ─────────────────────────────────────────────
  if (phase === 'done' && result) {
    const filtered = result.questions.filter(q2 =>
      filter === 'all' ? true : filter === 'ok' ? q2.is_correct : !q2.is_correct
    );
    return (
      <section className="screen" role="main" aria-label="Contenu principal">
        <div style={{ maxWidth: 720, margin: '0 auto', display: 'grid', gap: 18 }}>
          <div style={{ background: `linear-gradient(135deg,${result.passed ? 'var(--green)' : 'var(--navy)'},${result.passed ? '#006b47' : 'var(--navy2)'})`, borderRadius: 20, padding: 28, color: '#fff', textAlign: 'center' }}>
            <div style={{ fontSize: 48 }}>{result.passed ? '🏆' : '📋'}</div>
            <h2 style={{ color: '#fff', fontSize: 24, margin: '8px 0 4px' }}>{result.passed ? 'Félicitations — Admis !' : 'Ajourné'}</h2>
            <div style={{ fontSize: 40, fontWeight: 900 }}>{result.score} <span style={{ fontSize: 20, fontWeight: 500, opacity: .8 }}>/ {result.total}</span></div>
            <div style={{ fontSize: 14, opacity: .8 }}>{result.score_percent}% — Seuil : {result.threshold}/{result.total}</div>
            <div style={{ fontSize: 13, opacity: .65, marginTop: 4 }}>{result.candidate_name}</div>
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(['all','ok','ko'] as const).map(f => (
              <button key={f} type="button"
                className={filter === f ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
                onClick={() => setFilter(f)}>
                {f === 'all' ? `Toutes (${result.questions.length})`
                  : f === 'ok' ? `✅ Correctes (${result.questions.filter(q2 => q2.is_correct).length})`
                  : `❌ Incorrectes (${result.questions.filter(q2 => !q2.is_correct).length})`}
              </button>
            ))}
            <button className="secondary-button btn-sm" onClick={() => { setAnswers({}); setIdx(0); setPhase('setup'); setResult(null); }}>
              🔄 Recommencer
            </button>
          </div>

          {filtered.map(q2 => (
            <div key={q2.question_id} style={{ background: '#fff', border: `1.5px solid ${q2.is_correct ? '#86efac' : '#fca5a5'}`, borderRadius: 'var(--r-lg)', padding: '14px 18px', display: 'grid', gap: 7 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ background: 'var(--bg)', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>Q{q2.number}</span>
                <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--muted)', flex: 1 }}>{q2.category}</span>
                <span>{q2.is_correct ? '✅' : '❌'}</span>
              </div>
              <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--ink)', margin: 0 }}>{q2.text}</p>
              {!q2.is_correct && q2.given_answer && <p style={{ fontSize: 12, color: '#D32F2F', margin: 0 }}>Votre réponse : <strong>{q2.given_answer}</strong></p>}
              {!q2.is_correct && <p style={{ fontSize: 12, color: 'var(--green)', margin: 0 }}>Bonne réponse : <strong>{q2.correct_answer}</strong></p>}
              {q2.explanation && <p style={{ fontSize: 12, color: 'var(--muted)', background: 'var(--bg)', padding: '6px 10px', borderRadius: 8, margin: 0 }}>💡 {q2.explanation}</p>}
            </div>
          ))}
        </div>
      </section>
    );
  }

  // ── Running ────────────────────────────────────────────────────
  if (phase === 'review') {
    const unanswered = questions.filter((_, i) => answers[i] === undefined);
    return (
      <section className="screen" role="main" aria-label="Contenu principal">
        <div style={{ maxWidth: 520, margin: '0 auto' }} className="card">
          <h2 style={{ marginBottom: 12 }}>Vérification avant soumission</h2>
          <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>
            {answered}/{questions.length} questions répondues.
          </p>
          {unanswered.length > 0 && (
            <div style={{ display: 'grid', gap: 6, marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--gold)' }}>Questions sans réponse :</p>
              {unanswered.map(q2 => (
                <button key={q2.id} type="button" className="secondary-button btn-sm" style={{ justifyContent: 'flex-start' }}
                  onClick={() => { setIdx(q2.number - 1); setPhase('running'); }}>
                  Q{q2.number} — {q2.category}
                </button>
              ))}
            </div>
          )}
          <div className="actions">
            <button className="secondary-button" onClick={() => setPhase('running')}>↩ Revenir</button>
            <button className="btn-success" onClick={submitExam}>✅ Soumettre définitivement</button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="screen" style={{ padding: '16px 12px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 14, alignItems: 'start', maxWidth: 1100, margin: '0 auto' }}>
        {/* Sidebar */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: 16, display: 'grid', gap: 14, position: 'sticky', top: 76 }}>
          <Timer secs={SECS} total={SECS} onExpire={handleExpire} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700, color: 'var(--muted)' }}>
            <span><strong style={{ color: 'var(--ink)' }}>{answered}</strong> / {questions.length}</span>
            <span>Seuil : 35</span>
          </div>
          <QGrid total={questions.length} cur={idx} ans={answers} onSelect={i => { setReveal(false); setIdx(i); }} />
          <button className="btn-success btn-block btn-sm" onClick={() => answered < questions.length ? setPhase('review') : submitExam()}>
            {answered < questions.length ? `Vérifier (${questions.length - answered} sans réponse)` : '✅ Soumettre'}
          </button>
        </div>

        {/* Main */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px 22px', display: 'grid', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ background: 'var(--green-l)', color: 'var(--green)', padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>{q.category}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AudioToggle />
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)' }}>Q {idx + 1} / {questions.length}</span>
            </div>
          </div>

          <div style={{ height: 5, background: 'var(--bg)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ height: '100%', background: `linear-gradient(90deg,var(--blue),var(--green))`, borderRadius: 'inherit', width: `${(idx + 1) / questions.length * 100}%`, transition: 'width .3s' }} />
          </div>

          {/* Media */}
          {q.media && (
            <div style={{ background: q.mediaType === 'scene' ? '#1a2e1a' : '#f8fafc', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: 20, display: 'flex', justifyContent: 'center', minHeight: 140 }}>
              {q.mediaType === 'sign' ? <SignSvg type={q.media} /> : <SceneSvg type={q.media.replace('situation_','').replace('intersection_','')} />}
            </div>
          )}

          {/* Bouton écouter (visible pour toutes les locales, obligatoire pour les langues nationales) */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.5, flex: 1 }}>{q.text}</p>
            <PlayButton text={q.text} options={q.options} size={38} />
          </div>

          <div style={{ display: 'grid', gap: 8 }}>
            {q.options.map((opt, i) => {
              let bg = 'var(--bg)', border = 'var(--border)', color = 'var(--ink2)';
              if (answers[idx] === opt) { bg = '#dcfce7'; border = '#86efac'; color = '#166534'; }
              if (reveal && answers[idx] === opt && answers[idx] !== q.correct) { bg = '#fdecea'; border = '#fca5a5'; color = '#D32F2F'; }
              return (
                <button key={i} type="button" onClick={() => pick(opt)}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', border: `2px solid ${border}`, borderRadius: 'var(--r-lg)', background: bg, cursor: 'pointer', textAlign: 'left', width: '100%', color, fontSize: 13, fontWeight: 500, minHeight: 'unset', transition: 'all .15s' }}>
                  <span style={{ width: 26, height: 26, borderRadius: 7, background: answers[idx] === opt ? (answers[idx] === q.correct || !reveal ? 'var(--green)' : '#D32F2F') : '#e2e8f0', color: answers[idx] === opt ? '#fff' : 'var(--muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 900, flexShrink: 0 }}>
                    {String.fromCharCode(65 + i)}
                  </span>
                  <span style={{ flex: 1 }}>{opt}</span>
                  {answers[idx] === opt && <span>{answers[idx] === q.correct ? '✓' : '✗'}</span>}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 8, borderTop: '1px solid var(--border)' }}>
            <button className="secondary-button btn-sm" disabled={idx === 0} onClick={() => { setReveal(false); setIdx(i => Math.max(0, i - 1)); }}>← Précédente</button>
            <button className="secondary-button btn-sm" onClick={() => { setReveal(false); setIdx(i => Math.min(questions.length - 1, i + 1)); }}>Suivante →</button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// RESULTS PAGE
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
                  onClick={() => downloadExamCertificatePdf(attemptId).catch(() => undefined)}>
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
            <div key={q.question_id} style={{ background: '#fff', border: `1.5px solid ${q.is_correct ? '#86efac' : '#fca5a5'}`, borderRadius: 12, padding: '14px 16px', display: 'grid', gap: 7 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ background: 'var(--bg)', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>Q{q.number}</span>
                <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--muted)', flex: 1 }}>{q.category}</span>
                <span>{q.is_correct ? '✅' : '❌'}</span>
              </div>
              <p style={{ fontWeight: 600, fontSize: 13, margin: 0 }}>{q.text}</p>
              {!q.is_correct && q.given_answer && <p style={{ fontSize: 12, color: '#D32F2F', margin: 0 }}>Votre réponse : <strong>{q.given_answer}</strong></p>}
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

export function TrainingPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canUseApi = canUseProtectedActions(currentUser, isPresentationMode, ['candidate','admin','super_admin','driving_school']);

  type TrainingQ = {
    index: number; category: string; category_label: string;
    text: string; options: string[];
    correct_answer: string; explanation: string;
  };

  const CATS = [
    { id: '', label: 'Toutes les catégories', icon: '📚' },
    { id: 'signalisation',    label: 'Signalisation',          icon: '🚦' },
    { id: 'priorites',        label: 'Priorités',              icon: '⭐' },
    { id: 'vitesse',          label: 'Vitesse & Distances',    icon: '⏱️' },
    { id: 'depassement',      label: 'Dépassement',            icon: '↔️' },
    { id: 'securite_passive', label: 'Sécurité passive',       icon: '🛡️' },
    { id: 'urgence',          label: 'Situations d\'urgence',  icon: '🚨' },
    { id: 'alcool_drogues',   label: 'Alcool & Drogues',       icon: '🚫' },
    { id: 'premiers_secours', label: 'Premiers secours',       icon: '🩺' },
  ];

  const [mode, setMode] = useState<'menu'|'training'|'done'>('menu');
  const [cat, setCat] = useState('');
  const [questions, setQuestions] = useState<TrainingQ[]>([]);
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [stats, setStats] = useState<{ total: number; correct: number; bycat: Record<string,{ok:number;total:number}> }>({ total: 0, correct: 0, bycat: {} });

  // Charger les questions via l'API training
  async function startSession() {
    setLoading(true);
    try {
      const url = `/api/v1/training/questions?limit=20&shuffle=true${cat ? `&category=${cat}` : ''}`;
      let qs: TrainingQ[] = [];
      if (canUseApi) {
        const r = await fetch(url, { headers: { 'Authorization': `Bearer ${localStorage.getItem('cr-access-token') ?? ''}` } });
        if (r.ok) qs = await r.json();
      }
      if (qs.length === 0) {
        // Fallback local depuis les données DEMO_QUESTIONS
        qs = DEMO_QUESTIONS
          .filter(q => !cat || q.category === cat)
          .sort(() => Math.random() - .5).slice(0, 20)
          .map((q, i) => ({
            index: i, category: q.category, category_label: q.category,
            text: q.text, options: q.options,
            correct_answer: q.correct_answer, explanation: q.explanation ?? '',
          }));
      }
      setQuestions(qs); setQi(0); setAnswers({}); setRevealed(false);
      setMode('training');
    } finally { setLoading(false); }
  }

  function pickAnswer(opt: string) {
    if (revealed) return;
    setAnswers(a => ({ ...a, [qi]: opt }));
    setRevealed(true);
    // Feedback audio : correct ou incorrect (avec explication pour les mauvaises réponses)
    const isCorrect = opt === questions[qi]?.correct_answer;
    const expl = questions[qi]?.explanation ?? '';
    speakFeedback(isCorrect, expl);
  }

  function next() {
    setRevealed(false);
    if (qi < questions.length - 1) setQi(i => i + 1);
    else {
      // Calculer les stats
      const correct = questions.filter((q, i) => answers[i] === q.correct_answer).length;
      const bycat: Record<string,{ok:number;total:number}> = {};
      questions.forEach((q, i) => {
        if (!bycat[q.category]) bycat[q.category] = { ok: 0, total: 0 };
        bycat[q.category].total++;
        if (answers[i] === q.correct_answer) bycat[q.category].ok++;
      });
      setStats({ total: questions.length, correct, bycat });
      setMode('done');
    }
  }

  const q = questions[qi];

  // ── Menu ──────────────────────────────────────────────────────
  if (mode === 'menu') return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Module Entraînement</span>
        <h1>Préparez-vous à l'examen</h1>
        <p>200 questions classées par catégorie. Explication immédiate après chaque réponse.</p>
      </div>

      <div style={{ maxWidth: 700 }}>
        <AudioModeBanner />
        {/* Sélecteur de catégorie */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header"><span className="card-title">🎯 Choisissez une catégorie</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: 8 }}>
            {CATS.map(c => (
              <button key={c.id} type="button"
                className={cat === c.id ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
                style={{ justifyContent: 'flex-start', gap: 8 }}
                onClick={() => setCat(c.id)}>
                <span>{c.icon}</span> <span>{c.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Options */}
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">📖 Mode entraînement libre</span></div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14, display: 'grid', gap: 6 }}>
              <div>✅ Réponse correcte affichée immédiatement</div>
              <div>💡 Explication pédagogique après chaque question</div>
              <div>📊 Statistiques par catégorie en fin de session</div>
              <div>🔄 20 questions tirées aléatoirement</div>
            </div>
            <button className="btn-success btn-block btn-lg" onClick={startSession} disabled={loading}>
              {loading ? 'Chargement…' : '🚀 Démarrer l\'entraînement'}
            </button>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">📊 Statistiques globales</span></div>
            <div style={{ display: 'grid', gap: 10 }}>
              {CATS.slice(1).map(c => (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <span style={{ width: 24 }}>{c.icon}</span>
                  <span style={{ flex: 1, color: 'var(--ink2)' }}>{c.label}</span>
                  <span className="badge bb">
                    {DEMO_QUESTIONS.filter(q => q.category === c.id).length} Q
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  // ── Résultats entraînement ────────────────────────────────────
  if (mode === 'done') {
    const pct = Math.round(stats.correct / stats.total * 100);
    const weak = Object.entries(stats.bycat)
      .filter(([, v]) => v.ok / v.total < .7)
      .sort(([, a], [, b]) => (a.ok/a.total) - (b.ok/b.total));
    return (
      <section className="screen" role="main" aria-label="Contenu principal">
        <div style={{ maxWidth: 640, margin: '0 auto', display: 'grid', gap: 16 }}>
          <div style={{ background: `linear-gradient(135deg,${pct>=70?'var(--green)':'var(--navy)'},${pct>=70?'#006b47':'var(--navy2)'})`, borderRadius: 20, padding: '24px 28px', color: '#fff', textAlign: 'center' }}>
            <div style={{ fontSize: 44 }}>{pct >= 80 ? '🏆' : pct >= 60 ? '📈' : '📚'}</div>
            <h2 style={{ color: '#fff', fontSize: 22, margin: '8px 0 4px' }}>
              {pct >= 80 ? 'Excellent !' : pct >= 60 ? 'En progrès' : 'Continuez à réviser'}
            </h2>
            <div style={{ fontSize: 38, fontWeight: 900 }}>{stats.correct}<span style={{ fontSize: 18, opacity: .7 }}>/{stats.total}</span></div>
            <div style={{ fontSize: 14, opacity: .8 }}>{pct} % de bonnes réponses</div>
          </div>

          {weak.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">⚠️ Points à améliorer</span></div>
              {weak.map(([cat, v]) => (
                <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ flex: 1, fontSize: 13 }}>{CATS.find(c=>c.id===cat)?.icon} {CATS.find(c=>c.id===cat)?.label ?? cat}</span>
                  <span className="badge br">{v.ok}/{v.total}</span>
                </div>
              ))}
              <div style={{ marginTop: 14 }}>
                <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 10 }}>
                  Révisez les catégories faibles pour améliorer votre score.
                </p>
                <div className="actions">
                  {weak.slice(0,3).map(([c]) => (
                    <button key={c} type="button" className="secondary-button btn-sm"
                      onClick={() => { setCat(c); setMode('menu'); }}>
                      Retravailler {CATS.find(x=>x.id===c)?.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="actions">
            <button className="btn-success" onClick={() => { setMode('menu'); setQi(0); setAnswers({}); }}>🔄 Nouvelle session</button>
            <a href="#/exam"><button className="btn-primary">🎓 Passer l'examen officiel →</button></a>
          </div>
        </div>
      </section>
    );
  }

  // ── Question en cours ─────────────────────────────────────────
  const isCorrect = answers[qi] === q.correct_answer;
  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        {/* Progression */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, fontSize: 13, color: 'var(--muted)' }}>
          <span>{CATS.find(c=>c.id===q.category)?.icon} {q.category_label}</span>
          <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{qi+1} / {questions.length}</span>
        </div>
        <div style={{ height: 6, background: 'var(--border)', borderRadius: 99, marginBottom: 20, overflow: 'hidden' }}>
          <div style={{ height: '100%', background: `linear-gradient(90deg,var(--blue),var(--green))`, width: `${(qi+1)/questions.length*100}%`, borderRadius: 'inherit', transition: 'width .3s' }} />
        </div>

        {/* Question */}
        <div className="card" style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}>
            <p style={{ fontSize: 17, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.5, flex: 1, margin: 0 }}>{q.text}</p>
            <PlayButton text={q.text} options={q.options} size={40} />
          </div>

          <div style={{ display: 'grid', gap: 9 }}>
            {q.options.map((opt, i) => {
              let bg = 'var(--bg)', border = 'var(--border)', clr = 'var(--ink2)';
              if (revealed) {
                if (opt === q.correct_answer) { bg = 'var(--green-l)'; border = '#86efac'; clr = '#166534'; }
                else if (answers[qi] === opt) { bg = 'var(--red-l)'; border = '#fca5a5'; clr = 'var(--red)'; }
              } else if (answers[qi] === opt) {
                bg = 'var(--blue-l)'; border = 'var(--blue)'; clr = 'var(--blue)';
              }
              return (
                <button key={i} type="button" onClick={() => pickAnswer(opt)}
                  style={{ display:'flex', alignItems:'center', gap:10, padding:'12px 14px', border:`2px solid ${border}`, borderRadius:'var(--r-lg)', background:bg, cursor:'pointer', textAlign:'left', width:'100%', color:clr, fontSize:13, fontWeight:500, minHeight:'unset', transition:'all .15s' }}>
                  <span style={{ width:26, height:26, borderRadius:7, background: revealed ? (opt===q.correct_answer ? 'var(--green)' : answers[qi]===opt ? 'var(--red)' : '#e2e8f0') : (answers[qi]===opt ? 'var(--blue)' : '#e2e8f0'), color: revealed || answers[qi]===opt ? '#fff' : 'var(--muted)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:12, fontWeight:900, flexShrink:0 }}>
                    {String.fromCharCode(65+i)}
                  </span>
                  {opt}
                  {revealed && opt === q.correct_answer && <span style={{ marginLeft:'auto', fontWeight:900 }}>✓</span>}
                  {revealed && opt !== q.correct_answer && answers[qi] === opt && <span style={{ marginLeft:'auto', fontWeight:900 }}>✗</span>}
                </button>
              );
            })}
          </div>

          {/* Explication immédiate */}
          {revealed && q.explanation && (
            <div style={{ marginTop:16, background: isCorrect ? 'var(--green-l)' : 'var(--blue-l)', border:`1px solid ${isCorrect ? '#86efac' : '#bfdbfe'}`, borderRadius:'var(--r)', padding:'12px 14px', fontSize:13 }}>
              <div style={{ fontWeight:700, marginBottom:4, color: isCorrect ? '#166534' : 'var(--blue)' }}>
                {isCorrect ? '✅ Bonne réponse !' : '💡 Explication'}
              </div>
              <div style={{ color: 'var(--ink2)', lineHeight:1.5 }}>{q.explanation}</div>
            </div>
          )}
        </div>

        {/* Navigation */}
        {revealed && (
          <button className="btn-success btn-block btn-lg" onClick={next}>
            {qi < questions.length - 1 ? 'Question suivante →' : '📊 Voir mes résultats'}
          </button>
        )}
        {!revealed && (
          <div style={{ textAlign:'center', fontSize:13, color:'var(--muted)' }}>
            Sélectionnez une réponse pour voir l'explication
          </div>
        )}
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// DRIVING SCHOOL PAGE — Portail auto-école (Mois 10–12)
// ══════════════════════════════════════════════════════════════════
export function DrivingSchoolPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const isSchool = !isPresentationMode && currentUser?.role === 'driving_school';

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
          🏫 Mode démonstration — Connectez-vous avec un compte auto-école pour voir vos élèves réels.
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
                      {s.status==='pret' ? '✅ Prêt' : s.status==='risque' ? '⚠️ Risque' : s.status==='en_cours' ? '📈 En cours' : '🆕 Débutant'}
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
          ⚠️ <strong>{risque} élève(s) en difficulté</strong> — Leur score moyen est inférieur à 28/40.
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
          <div className="card-header"><span className="card-title">📋 Actions rapides</span></div>
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


export function MinisterialPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAdmin = canUseProtectedActions(currentUser, isPresentationMode, ['admin','super_admin']);

  const [tab, setTab] = useState<'overview'|'import'|'stations'|'alerts'>('overview');
  const [opSummary, setOpSummary] = useState<OperationsSummary | null>(null);
  const [readiness, setReadiness] = useState<InstitutionalReadiness | null>(null);
  const [actionCenter, setActionCenter] = useState<InstitutionalActionCenter | null>(null);
  const [loading, setLoading] = useState(true);

  // Import candidats
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importType, setImportType] = useState<'candidates'|'centers'|'questions'>('candidates');
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  // Stations
  const [stations, setStations] = useState<import('./api').CenterStation[]>([]);
  const [stLabel, setStLabel] = useState('');
  const [stRoom, setStRoom] = useState('');
  const [stCenter, setStCenter] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    Promise.allSettled([
      getOperationsSummary(),
      getInstitutionalReadiness(),
      getInstitutionalActionCenter(),
    ]).then(([op, rd, ac]) => {
      if (op.status === 'fulfilled') setOpSummary(op.value);
      if (rd.status === 'fulfilled') setReadiness(rd.value);
      if (ac.status === 'fulfilled') setActionCenter(ac.value);
    }).finally(() => setLoading(false));
  }, [canAdmin]);

  useEffect(() => {
    if (tab === 'stations' && canAdmin) {
      getCenterStations({ limit: 50 }).then(setStations).catch(() => undefined);
    }
  }, [tab, canAdmin]);

  // ── Import CSV ──────────────────────────────────────────────────
  async function handleImport(e: FormEvent) {
    e.preventDefault();
    if (!importFile || !canAdmin) return;
    setImporting(true); setImportStatus(null);
    try {
      const text = await importFile.text();
      const lines = text.trim().split('\n').slice(1); // skip header
      const count = lines.length;

      if (importType === 'candidates') {
        const rows = lines.map(l => {
          const [last, first, nina, phone, cat] = l.split(',').map(s => s.trim().replace(/"/g,''));
          return { last_name: last, first_name: first, identity_number: nina, phone, permit_category: cat || 'B', status: 'registered' as const };
        });
        const r = await importOfficialCandidates('csv_import', `Import CSV ${importFile.name}`, rows, true);
        setImportStatus(`✅ Aperçu import : ${r.created ?? 0} nouveaux, ${r.skipped ?? 0} ignorés sur ${count} lignes`);
      } else if (importType === 'centers') {
        const rows = lines.map(l => {
          const [code, name, city, address, cap] = l.split(',').map(s => s.trim().replace(/"/g,''));
          return { code, name, city, address, capacity: parseInt(cap) || 30, status: 'pending_audit' as const };
        });
        const r = await importOfficialCenters('csv_import', `Import CSV ${importFile.name}`, rows, true);
        setImportStatus(`✅ Aperçu import : ${r.created ?? 0} nouveaux centres sur ${count} lignes`);
      } else {
        const rows = lines.map(l => {
          const [cat, text, opt1, opt2, opt3, opt4, correct] = l.split(',').map(s => s.trim().replace(/"/g,''));
          return { category: cat, text, options: [opt1,opt2,opt3,opt4].filter(Boolean), correct_answer: correct, is_active: true };
        });
        const r = await importOfficialQuestions('csv_import', `Import CSV ${importFile.name}`, rows, true);
        setImportStatus(`✅ Aperçu import : ${r.created ?? 0} nouvelles questions sur ${count} lignes`);
      }
    } catch (err) {
      setImportStatus(`❌ Erreur import : ${errMsg(err)}`);
    } finally { setImporting(false); }
  }

  async function handleCreateStation(e: FormEvent) {
    e.preventDefault();
    if (!stLabel || !stCenter) return;
    setCreating(true);
    try {
      await createCenterStation({ center_id: stCenter, label: stLabel, room: stRoom, status: 'active', device_key: stLabel.toUpperCase().replace(/\s+/g,'-') });
      getCenterStations({ limit: 50 }).then(setStations).catch(() => undefined);
      setStLabel(''); setStRoom('');
    } catch (err) {
      alert(errMsg(err));
    } finally { setCreating(false); }
  }

  const TABS = [
    { id: 'overview', label: '📊 Vue nationale' },
    { id: 'import',   label: '📥 Imports officiels' },
    { id: 'stations', label: '🖥️ Postes d\'examen' },
    { id: 'alerts',   label: '⚠️ Centre d\'action' },
  ] as const;

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Portail ministériel</span>
        <h1>Tableau de bord national — DNTT</h1>
        <p>Pilotage stratégique de la plateforme nationale d'examen du code de la route.</p>
      </div>

      {!canAdmin && (
        <div className="alert aw">⚠️ Réservé aux administrateurs nationaux et super_admin.</div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} type="button"
            className={tab === t.id ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
            onClick={() => setTab(t.id as typeof tab)}>
            {t.label}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="secondary-button btn-sm" onClick={() => downloadInstitutionalReportCsv().catch(() => undefined)}>⬇ Rapport CSV</button>
          <button className="secondary-button btn-sm" onClick={() => downloadInstitutionalReportPdf().catch(() => undefined)}>⬇ Rapport PDF</button>
        </div>
      </div>

      {/* ── Vue nationale ── */}
      {tab === 'overview' && (
        <>
          {loading ? <div style={{ textAlign: 'center', padding: 48, color: 'var(--muted)' }}>Chargement des données nationales…</div> : (
            <>
              {opSummary && (
                <div className="stats-grid" style={{ marginBottom: 20 }}>
                  <div className="stat-card s-blue"><div className="stat-label">Alertes critiques</div><div className="stat-value">{fmt(opSummary.critical_alerts ?? 0)}</div></div>
                  <div className="stat-card s-green"><div className="stat-label">Candidats aujourd'hui</div><div className="stat-value">{fmt(opSummary.open_incidents ?? 0)}</div></div>
                  <div className="stat-card s-gold"><div className="stat-label">Taux de réussite</div><div className="stat-value">{opSummary.high_risk_exam_events ?? 0}<span style={{fontSize:16}}>%</span></div></div>
                  <div className="stat-card s-red"><div className="stat-label">Alertes fraude</div><div className="stat-value">{fmt(opSummary.payment_alerts ?? 0)}</div></div>
                </div>
              )}

              {/* Carte du taux de réussite par préfecture — simulé */}
              <div className="g2">
                <div className="card">
                  <div className="card-header"><span className="card-title">🗺️ Taux de réussite par région</span></div>
                  {[
                    { region: 'Conakry', taux: 72, candidats: 48320, centres: 12 },
                    { region: 'Kindia', taux: 68, candidats: 12400, centres: 4 },
                    { region: 'Labé', taux: 65, candidats: 9800, centres: 3 },
                    { region: 'Kankan', taux: 61, candidats: 11200, centres: 4 },
                    { region: 'N\'Zérékoré', taux: 58, candidats: 8900, centres: 3 },
                    { region: 'Faranah', taux: 55, candidats: 6100, centres: 2 },
                    { region: 'Mamou', taux: 63, candidats: 7400, centres: 3 },
                    { region: 'Boké', taux: 60, candidats: 6800, centres: 2 },
                  ].map(r => (
                    <div key={r.region} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
                      <span style={{ fontWeight:600, minWidth:100, fontSize:13 }}>{r.region}</span>
                      <div style={{ flex:1, height:8, background:'var(--border)', borderRadius:99, overflow:'hidden' }}>
                        <div style={{ height:'100%', background: r.taux>=70?'var(--green)':r.taux>=60?'var(--gold)':'var(--red)', width:`${r.taux}%`, borderRadius:'inherit' }}/>
                      </div>
                      <span style={{ fontWeight:800, minWidth:36, color: r.taux>=70?'var(--green)':r.taux>=60?'#b7620a':'var(--red)', fontSize:13 }}>{r.taux}%</span>
                      <span style={{ fontSize:11, color:'var(--muted)', minWidth:80, textAlign:'right' }}>{fmt(r.candidats)} candidats</span>
                    </div>
                  ))}
                </div>

                <div className="card">
                  <div className="card-header"><span className="card-title">📈 Indicateurs clés</span></div>
                  <div style={{ display:'grid', gap:14 }}>
                    {readiness?.items?.slice(0,6).map((item: import('./api').InstitutionalReadinessItem, i: number) => (
                      <div key={i} style={{ display:'flex', alignItems:'center', gap:10 }}>
                        <span style={{ fontSize:20 }}>{item.status === 'ready' ? '✅' : item.status === 'partial' ? '⚠️' : '❌'}</span>
                        <div style={{ flex:1 }}>
                          <div style={{ fontSize:13, fontWeight:600 }}>{(item as {pillar?:string; label?:string}).pillar ?? (item as {label?:string}).label ?? ""}</div>
                          <div style={{ fontSize:11, color:'var(--muted)' }}>{(item as {evidence?:string; val?:string}).evidence ?? (item as {val?:string}).val ?? ""}</div>
                        </div>
                      </div>
                    )) ?? (
                      <>
                        {[
                          { label:'Couverture nationale', val:'8 régions / 33 préfectures', ok:true },
                          { label:'Uptime plateforme', val:'99,7 % (30 derniers jours)', ok:true },
                          { label:'Données synchronisées', val:'Temps réel', ok:true },
                          { label:'Backup dernière exécution', val:'Aujourd\'hui 02h00', ok:true },
                          { label:'Certification SSL', val:'Valide — expiration dans 89 jours', ok:true },
                          { label:'Intégration NINA', val:'Non connectée', ok:false },
                        ].map((item, i) => (
                          <div key={i} style={{ display:'flex', alignItems:'center', gap:10 }}>
                            <span>{item.ok ? '✅' : '⚠️'}</span>
                            <div style={{ flex:1 }}>
                              <div style={{ fontSize:13, fontWeight:600 }}>{(item as {pillar?:string; label?:string}).pillar ?? (item as {label?:string}).label ?? ""}</div>
                              <div style={{ fontSize:11, color:'var(--muted)' }}>{item.val}</div>
                            </div>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* ── Imports officiels ── */}
      {tab === 'import' && (
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">📥 Import CSV officiel</span></div>
            <form onSubmit={handleImport} style={{ display:'grid', gap:14 }}>
              <label>
                Type d'import
                <select value={importType} onChange={e => setImportType(e.target.value as typeof importType)} aria-label="Type d'import">
                  <option value="candidates">Candidats</option>
                  <option value="centers">Centres agréés</option>
                  <option value="questions">Questions banque</option>
                </select>
              </label>
              <label>
                Fichier CSV
                <input type="file" accept=".csv,.txt"
                  onChange={e => setImportFile(e.target.files?.[0] ?? null)}
                  style={{ padding:'6px 0' }} />
              </label>
              {importStatus && (
                <div className={`alert ${importStatus.startsWith('✅') ? 'as' : 'ae'}`}>
                  {importStatus}
                </div>
              )}
              <button type="submit" className="btn-primary" disabled={!importFile || importing}>
                {importing ? 'Import en cours…' : '📥 Aperçu (dry-run)'}
              </button>
              <p style={{ fontSize:12, color:'var(--muted)' }}>
                ℹ️ L'aperçu vérifie le fichier sans modifier les données. Confirmez ensuite pour valider l'import réel.
              </p>
            </form>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">📋 Format CSV attendu</span></div>
            <div style={{ display:'grid', gap:14 }}>
              {[
                {
                  type: 'Candidats',
                  header: 'nom,prenom,nina,telephone,categorie',
                  example: 'Diallo,Mamadou,GN-NINA-001,+224620000001,B',
                },
                {
                  type: 'Centres',
                  header: 'code,nom,ville,adresse,capacite',
                  example: 'CTR-001,Centre Kaloum,Conakry,Rue KA-001,50',
                },
                {
                  type: 'Questions',
                  header: 'categorie,texte,opt1,opt2,opt3,opt4,correct',
                  example: 'signalisation,"Que signifie ce panneau ?",Arrêt,Céder,...,Arrêt',
                },
              ].filter(f => f.type.toLowerCase().includes(importType.slice(0,4))).map(f => (
                <div key={f.type}>
                  <div style={{ fontSize:12, fontWeight:700, color:'var(--navy)', marginBottom:4 }}>{f.type}</div>
                  <div style={{ background:'var(--bg)', borderRadius:'var(--r)', padding:'8px 12px', fontFamily:'monospace', fontSize:11, color:'var(--ink2)' }}>
                    <div style={{ color:'var(--blue)', marginBottom:2 }}>{f.header}</div>
                    <div>{f.example}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Postes d'examen ── */}
      {tab === 'stations' && (
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">➕ Créer un poste d'examen</span></div>
            <form onSubmit={handleCreateStation} style={{ display:'grid', gap:12 }}>
              <label>Centre (ID)<input value={stCenter} onChange={e => setStCenter(e.target.value)} placeholder="UUID du centre" /></label>
              <label>Label du poste<input value={stLabel} onChange={e => setStLabel(e.target.value)} placeholder="POSTE-01" /></label>
              <label>Salle<input value={stRoom} onChange={e => setStRoom(e.target.value)} placeholder="Salle A" /></label>
              <button type="submit" className="btn-primary" disabled={creating || !stLabel || !stCenter}>
                {creating ? 'Création…' : 'Créer le poste'}
              </button>
            </form>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">🖥️ Postes configurés ({stations.length})</span>
              <button className="secondary-button btn-sm" onClick={() => getCenterStations({ limit:50 }).then(setStations).catch(()=>undefined)}>
                Actualiser
              </button>
            </div>
            {stations.length === 0 ? (
              <div style={{ padding:'24px', textAlign:'center', color:'var(--muted)', fontSize:13 }}>
                {canAdmin ? 'Aucun poste configuré.' : 'Connectez-vous.'}
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Label</th><th>Salle</th><th>Statut</th></tr></thead>
                  <tbody>
                    {stations.map(s => (
                      <tr key={s.id}>
                        <td style={{ fontWeight:600 }}>{s.label}</td>
                        <td>{s.room ?? '—'}</td>
                        <td><span className={`badge ${s.status==='available'?'bg':s.status==='occupied'?'br':'bgr'}`}>{s.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Centre d'action ── */}
      {tab === 'alerts' && (
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">⚠️ Alertes nationales</span></div>
            {actionCenter?.items?.length ? (
              <div style={{ display:'grid', gap:12 }}>
                {actionCenter.items.map((item: import('./api').InstitutionalActionItem, i: number) => (
                  <div key={i} style={{ background:item.severity==='critical'?'var(--red-l)':item.severity==='warning'?'var(--gold-l)':'var(--blue-l)', border:`1px solid ${item.severity==='critical'?'#fca5a5':item.severity==='warning'?'#fde68a':'#bfdbfe'}`, borderRadius:'var(--r)', padding:'12px 14px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                      <span>{item.severity==='critical'?'🔴':item.severity==='warning'?'🟡':'🔵'}</span>
                      <strong style={{ fontSize:13 }}>{item.label}</strong>
                      <span className={`badge ${item.severity==='critical'?'br':item.severity==='warning'?'bgo':'bb'}`} style={{ marginLeft:'auto' }}>{item.severity}</span>
                    </div>
                    <p style={{ fontSize:12, color:'var(--muted)', margin:0 }}>{item.target} — {item.count}</p>
                  </div>
                ))}
              </div>
            ) : (
              <>
                {/* Alertes simulées representant la réalité du pilote */}
                {[
                  { sev:'high', title:'Centre de Kankan — taux de réussite anormal', desc:'98,5 % de réussite sur 30 jours consécutifs. Investigation DNTT recommandée.', action:'Planifier audit' },
                  { sev:'medium', title:'5 candidats avec résultats en attente > 48h', desc:'Les résultats de la session du 18/06 ne sont pas encore synchronisés.', action:'Vérifier sync' },
                  { sev:'low', title:'Renouvellement SSL dans 89 jours', desc:'Le certificat TLS de api.coderoute.gov.gn expire le 17/09/2026.', action:'Programmer renouvellement' },
                ].map((a, i) => (
                  <div key={i} style={{ background: a.sev==='critical'?'var(--red-l)':a.sev==='medium'?'var(--gold-l)':'var(--blue-l)', border:`1px solid ${a.sev==='critical'?'#fca5a5':a.sev==='medium'?'#fde68a':'#bfdbfe'}`, borderRadius:'var(--r)', padding:'12px 14px', marginBottom:10 }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                      <span>{a.sev==='critical'?'🔴':a.sev==='medium'?'🟡':'🔵'}</span>
                      <strong style={{ fontSize:13, flex:1 }}>{a.title}</strong>
                      <button className={`btn-sm ${a.sev==='critical'?'btn-danger':a.sev==='medium'?'btn-gold':'secondary-button'}`}>{a.action}</button>
                    </div>
                    <p style={{ fontSize:12, color:'var(--muted)', margin:0 }}>{a.desc}</p>
                  </div>
                ))}
              </>
            )}
          </div>

          {/* KPI anti-fraude */}
          <div className="card">
            <div className="card-header"><span className="card-title">🛡️ Anti-fraude — Vue nationale</span></div>
            <div style={{ display:'grid', gap:14, fontSize:13 }}>
              {[
                { icon:'📊', label:'Centres sous surveillance', val:'3 / 35 centres', color:'var(--gold)' },
                { icon:'🔍', label:'Examens avec anomalies détectées', val:'12 ce mois', color:'var(--red)' },
                { icon:'✅', label:'Taux d\'intégrité global', val:'96,8 %', color:'var(--green)' },
                { icon:'📡', label:'Postes hors ligne', val:'2 postes à Kindia', color:'var(--gold)' },
                { icon:'🎯', label:'Fraude détectée et bloquée', val:'7 tentatives', color:'var(--navy)' },
                { icon:'📱', label:'QR codes vérifiés par tiers', val:'1 249 ce mois', color:'var(--blue)' },
              ].map((k, i) => (
                <div key={i} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
                  <span style={{ fontSize:22 }}>{k.icon}</span>
                  <div style={{ flex:1 }}>
                    <div style={{ fontWeight:600, color:'var(--ink)' }}>{k.label}</div>
                  </div>
                  <span style={{ fontWeight:800, color:k.color, fontSize:14 }}>{k.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
