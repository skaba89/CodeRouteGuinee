import { type FormEvent, useEffect, useState } from 'react';

import {
  type Center,
  type AuditLogEntry,
  type CandidateIdentityCheck,
  type DashboardData,
  type EntrySummary,
  type EntryValidationResult,
  type ExamCertificateVerification,
  type ExamSummary,
  type InstitutionalAuthorization,
  type InstitutionalAuthorizationPayload,
  type InstitutionalReadiness,
  type PaymentAlert,
  type PaymentFilters,
  type PaymentReconciliationItem,
  type PaymentResult,
  type PaymentSummary,
  type QuestionGovernanceItem,
  createInstitutionalAuthorization,
  createPayment,
  decideCandidateIdentity,
  decideQuestionGovernance,
  downloadAdminPaymentsCsv,
  downloadDashboardCsv,
  downloadExamAttemptsCsv,
  getAdminPaymentSummary,
  getAuditLogs,
  getCandidateIdentityChecks,
  getCenters,
  getConvocationPdfUrl,
  getDashboard,
  getEntrySummary,
  getExamCertificatePdfUrl,
  getExamSummary,
  getInstitutionalReadiness,
  getInstitutionalAuthorizations,
  getPaymentAlerts,
  getPaymentReconciliationItems,
  getQuestionGovernanceItems,
  validateEntry,
  updateCenterStatus,
  updateInstitutionalAuthorizationStatus,
  verifyExamCertificate,
} from './api';

const fallbackDashboard: DashboardData = {
  candidates: 1250,
  accredited_centers: 18,
  exam_sessions: 96,
  questions: 0,
  fraud_alerts: 19,
};

const fallbackEntrySummary: EntrySummary = {
  total: 421,
  by_result: { allowed: 402, denied: 19 },
  by_center: {
    'CTR-KALOUM': { allowed: 122, denied: 3 },
    'CTR-MATOTO': { allowed: 98, denied: 12 },
    'CTR-KANKAN': { allowed: 66, denied: 4 },
  },
};

const fallbackExamSummary: ExamSummary = {
  total_attempts: 118,
  submitted_attempts: 104,
  passed_attempts: 74,
  failed_attempts: 30,
  average_score: 34.8,
};

const fallbackPaymentSummary: PaymentSummary = {
  total_count: 0,
  total_amount_gnf: 0,
  by_status: {},
  by_provider: {},
};

const fallbackInstitutionalReadiness: InstitutionalReadiness = {
  score: 70,
  label: 'Mode demonstration - pilote a renforcer',
  summary: 'Vue de demonstration pour presenter la trajectoire institutionnelle de CodeRoute Guinee.',
  items: [
    {
      pillar: 'Gouvernance nationale',
      status: 'partial',
      evidence: 'Mode demo : centres agrees, roles et supervision nationale sont modelises.',
      next_step: 'Faire valider la gouvernance par le ministere et les directions competentes.',
    },
    {
      pillar: 'Parcours candidat',
      status: 'ready',
      evidence: 'Inscription, reservation, paiement, convocation et resultats sont couverts.',
      next_step: 'Brancher les registres officiels et les pieces d identite.',
    },
    {
      pillar: 'Banque nationale de questions',
      status: 'partial',
      evidence: 'Le moteur de questions et correction automatique est operationnel.',
      next_step: 'Importer une banque officielle par categorie de permis.',
    },
    {
      pillar: 'Tracabilite et audit',
      status: 'ready',
      evidence: 'Les actions sensibles generent des journaux consultables.',
      next_step: 'Definir les durees de conservation et habilitations.',
    },
    {
      pillar: 'Securite antifraude',
      status: 'partial',
      evidence: 'Controle entree, monitoring examen et alertes sont presents.',
      next_step: 'Ajouter verification photo et supervision physique renforcee.',
    },
  ],
};

const fallbackIdentityChecks: CandidateIdentityCheck[] = [
  {
    id: 'demo-identity-1',
    candidate_id: 'GN-CODE-2026-000001',
    document_type: 'national_id',
    document_reference: 'NINA-DEMO-001',
    photo_reference: 'photo-controle-centre',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
  {
    id: 'demo-identity-2',
    candidate_id: 'GN-CODE-2026-000002',
    document_type: 'passport',
    document_reference: 'P-GN-DEMO-44',
    status: 'needs_review',
    decision_reason: 'Controle manuel requis avant convocation',
    created_at: new Date().toISOString(),
  },
];

const fallbackQuestionGovernance: QuestionGovernanceItem[] = [
  {
    question_id: 'demo-question-1',
    category: 'signalisation',
    text: 'Que doit faire un conducteur face a un feu rouge fixe ?',
    is_active: true,
    latest_status: 'published',
    latest_reason: 'Question officielle de demonstration',
    decided_at: new Date().toISOString(),
  },
  {
    question_id: 'demo-question-2',
    category: 'priorite',
    text: 'Dans quel cas la priorite a droite s applique-t-elle ?',
    is_active: false,
    latest_status: 'needs_revision',
    latest_reason: 'Relecture pedagogique requise',
    decided_at: new Date().toISOString(),
  },
];

const fallbackInstitutionalAuthorizations: InstitutionalAuthorization[] = [
  {
    id: 'demo-authz-1',
    authority: 'Ministere des Transports',
    reference: 'MT-CODE-DEMO-001',
    title: 'Convention pilote CodeRoute Guinee',
    scope: 'Digitalisation pilote des examens du code de la route en centre agree.',
    status: 'approved',
    valid_from: new Date().toISOString(),
    valid_until: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
  },
  {
    id: 'demo-authz-2',
    authority: 'Direction Nationale des Transports Terrestres',
    reference: 'DNTT-AUDIT-DEMO',
    title: 'Cadre de supervision des centres agrees',
    scope: 'Habilitation pour le suivi audit, suspension et accreditation des centres.',
    status: 'pending_signature',
    created_at: new Date().toISOString(),
  },
];

const modules = [
  'Inscription candidat',
  'Reservation examen',
  'Paiement Mobile Money',
  'Convocation QR et PDF',
  'Controle entree centre',
  'Examen et correction',
  'Logs et supervision',
  'Dashboard national',
];

function formatNumber(value: number): string {
  return new Intl.NumberFormat('fr-FR').format(value);
}

function formatCurrency(value: number): string {
  return `${formatNumber(value)} GNF`;
}

function buildRiskLabel(denied: number): string {
  if (denied >= 10) return 'A verifier';
  if (denied >= 4) return 'Audit';
  return 'Normal';
}

function formatAuditDetails(details?: AuditLogEntry['details']): string {
  if (!details) return 'Aucun detail';
  const entries = Object.entries(details).slice(0, 3);
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(' | ');
}

function sanitizePaymentFilters(filters: PaymentFilters): PaymentFilters {
  return {
    provider: filters.provider || undefined,
    status: filters.status || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  };
}

export function HomePage() {
  const [dashboard, setDashboard] = useState<DashboardData>(fallbackDashboard);
  const [apiStatus, setApiStatus] = useState<'connected' | 'offline'>('offline');

  useEffect(() => {
    getDashboard()
      .then((data) => {
        setDashboard(data);
        setApiStatus('connected');
      })
      .catch(() => setApiStatus('offline'));
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

export function CandidatePage() {
  const [bookingReference, setBookingReference] = useState('GN-BOOK-2026-000001');
  const [amount, setAmount] = useState(250000);
  const [provider, setProvider] = useState('orange_money');
  const [phone, setPhone] = useState('+224622000000');
  const [paymentResult, setPaymentResult] = useState<PaymentResult | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);
  const convocationUrl = getConvocationPdfUrl(bookingReference);

  async function handlePaymentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPaying(true);
    setPaymentError(null);
    setPaymentResult(null);
    try {
      const result = await createPayment({ booking_reference: bookingReference, amount_gnf: amount, provider, phone });
      setPaymentResult(result);
    } catch (error) {
      setPaymentError("Impossible de traiter le paiement. Verifiez que l'API est demarree.");
    } finally {
      setIsPaying(false);
    }
  }

  return (
    <section className="screen two-columns">
      <div>
        <p className="eyebrow dark">Espace candidat</p>
        <h2>Dossier, reservation et convocation</h2>
        <p>Le candidat suit son dossier, reserve une session, paie et telecharge sa convocation PDF avec QR code.</p>
        <div className="mini-card">Reference candidat : <strong>GN-CODE-2026-000001</strong></div>
        <div className="mini-card">Session : <strong>Centre Kaloum - 20/06/2026</strong></div>
        <div className="mini-card">Paiement : <strong>{paymentResult?.status ?? 'En attente'}</strong></div>
        <form className="payment-form" onSubmit={handlePaymentSubmit}>
          <h2>Paiement Mobile Money</h2>
          <label>Reference reservation<input value={bookingReference} onChange={(event) => setBookingReference(event.target.value)} /></label>
          <label>Montant GNF<input type="number" value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label>
          <label>Operateur<input value={provider} onChange={(event) => setProvider(event.target.value)} /></label>
          <label>Telephone<input value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <button disabled={isPaying}>{isPaying ? 'Traitement...' : 'Payer maintenant'}</button>
        </form>
      </div>
      <div className="qr-card">
        <div className="qr-box" />
        <strong>Convocation verifiable</strong>
        <span>{bookingReference}</span>
        <a className="download-link" href={convocationUrl} target="_blank" rel="noreferrer">Telecharger la convocation PDF</a>
        {paymentResult && (
          <div className="payment-result">
            <strong>Recu : {paymentResult.receipt_number}</strong>
            <span>Reference : {paymentResult.reference}</span>
            <span>Statut : {paymentResult.status}</span>
          </div>
        )}
        {paymentError && <p className="form-error">{paymentError}</p>}
      </div>
    </section>
  );
}

export function CenterPage() {
  const [entryReference, setEntryReference] = useState('GN-CONV-2026-000001');
  const [verificationCode, setVerificationCode] = useState('');
  const [centerCode, setCenterCode] = useState('CTR-KALOUM');
  const [entryResult, setEntryResult] = useState<EntryValidationResult | null>(null);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [isSubmittingEntry, setIsSubmittingEntry] = useState(false);

  async function handleEntrySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmittingEntry(true);
    setEntryError(null);
    setEntryResult(null);
    try {
      const result = await validateEntry({ reference: entryReference, verification_code: verificationCode, center_code: centerCode });
      setEntryResult(result);
    } catch (error) {
      setEntryError("Impossible de valider l'entree. Verifiez que l'API est demarree.");
    } finally {
      setIsSubmittingEntry(false);
    }
  }

  return (
    <section className="screen two-columns inverted">
      <form className="scanner-card" onSubmit={handleEntrySubmit}>
        <h2>Controle entree centre</h2>
        <p>Scan QR, verification du code et passage automatique du statut en checked_in.</p>
        <label>Reference convocation<input value={entryReference} onChange={(event) => setEntryReference(event.target.value)} /></label>
        <label>Code verification<input value={verificationCode} onChange={(event) => setVerificationCode(event.target.value)} placeholder="Code de la convocation" /></label>
        <label>Code centre<input value={centerCode} onChange={(event) => setCenterCode(event.target.value)} /></label>
        <button disabled={isSubmittingEntry || !entryReference || !verificationCode}>{isSubmittingEntry ? 'Validation...' : 'Valider entree'}</button>
      </form>
      <div>
        <p className="eyebrow dark">Centre agree</p>
        <h2>Validation en temps reel</h2>
        <table>
          <tbody>
            <tr><th>Statut</th><td><span className={entryResult?.allowed ? 'badge ok' : 'badge'}>{entryResult?.status ?? 'En attente'}</span></td></tr>
            <tr><th>Reference</th><td>{entryResult?.reference ?? entryReference}</td></tr>
            <tr><th>Centre</th><td>{entryResult?.center_code ?? centerCode}</td></tr>
            <tr><th>Message</th><td>{entryResult?.message ?? entryResult?.reason ?? entryError ?? 'Aucune validation lancee'}</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function AdminPage() {
  const [dashboard, setDashboard] = useState<DashboardData>(fallbackDashboard);
  const [centers, setCenters] = useState<Center[]>([]);
  const [centerStatus, setCenterStatus] = useState<string | null>(null);
  const [entrySummary, setEntrySummary] = useState<EntrySummary>(fallbackEntrySummary);
  const [examSummary, setExamSummary] = useState<ExamSummary>(fallbackExamSummary);
  const [paymentSummary, setPaymentSummary] = useState<PaymentSummary>(fallbackPaymentSummary);
  const [paymentItems, setPaymentItems] = useState<PaymentReconciliationItem[]>([]);
  const [paymentAlerts, setPaymentAlerts] = useState<PaymentAlert[]>([]);
  const [identityChecks, setIdentityChecks] = useState<CandidateIdentityCheck[]>(fallbackIdentityChecks);
  const [identityStatus, setIdentityStatus] = useState<string | null>(null);
  const [questionGovernance, setQuestionGovernance] = useState<QuestionGovernanceItem[]>(fallbackQuestionGovernance);
  const [questionGovernanceStatus, setQuestionGovernanceStatus] = useState<string | null>(null);
  const [institutionalAuthorizations, setInstitutionalAuthorizations] = useState<InstitutionalAuthorization[]>(fallbackInstitutionalAuthorizations);
  const [authorizationStatus, setAuthorizationStatus] = useState<string | null>(null);
  const [authorizationForm, setAuthorizationForm] = useState<InstitutionalAuthorizationPayload>({
    authority: 'Ministere des Transports',
    reference: 'MT-CODE-2026-001',
    title: 'Convention pilote CodeRoute Guinee',
    scope: 'Autorisation pilote pour la digitalisation des examens du code de la route.',
  });
  const [institutionalReadiness, setInstitutionalReadiness] = useState<InstitutionalReadiness>(fallbackInstitutionalReadiness);
  const [readinessStatus, setReadinessStatus] = useState<string | null>(null);
  const [paymentFilters, setPaymentFilters] = useState<PaymentFilters>({});
  const [activePaymentFilters, setActivePaymentFilters] = useState<PaymentFilters>({});
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditStatus, setAuditStatus] = useState<string | null>(null);
  const [financeStatus, setFinanceStatus] = useState<string | null>(null);
  const [csvExportStatus, setCsvExportStatus] = useState<string | null>(null);
  const [examCsvExportStatus, setExamCsvExportStatus] = useState<string | null>(null);
  const [paymentCsvExportStatus, setPaymentCsvExportStatus] = useState<string | null>(null);
  const [isExportingCsv, setIsExportingCsv] = useState(false);
  const [isExportingExamCsv, setIsExportingExamCsv] = useState(false);
  const [isExportingPaymentCsv, setIsExportingPaymentCsv] = useState(false);

  async function loadPaymentSummary(filters: PaymentFilters) {
    try {
      const cleanFilters = sanitizePaymentFilters(filters);
      const summary = await getAdminPaymentSummary(cleanFilters);
      const items = await getPaymentReconciliationItems({ ...cleanFilters, limit: 25 });
      const alerts = await getPaymentAlerts({ ...cleanFilters, limit: 25 });
      setPaymentSummary(summary);
      setPaymentItems(items);
      setPaymentAlerts(alerts);
      setActivePaymentFilters(cleanFilters);
      setFinanceStatus(null);
    } catch {
      setFinanceStatus('Finance indisponible : connectez-vous avec un role admin ou super admin.');
    }
  }

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => undefined);
    getCenters().then(setCenters).catch(() => undefined);
    getEntrySummary().then(setEntrySummary).catch(() => undefined);
    getExamSummary().then(setExamSummary).catch(() => undefined);
    loadPaymentSummary({});
    getInstitutionalReadiness()
      .then((readiness) => {
        setInstitutionalReadiness(readiness);
        setReadinessStatus(null);
      })
      .catch(() => setReadinessStatus('Mode demo : connectez-vous avec un token admin pour charger le score institutionnel API.'));
    getCandidateIdentityChecks()
      .then((checks) => {
        setIdentityChecks(checks.length > 0 ? checks : fallbackIdentityChecks);
        setIdentityStatus(null);
      })
      .catch(() => setIdentityStatus('Mode demo : connectez-vous avec un role admin pour traiter les identites API.'));
    getQuestionGovernanceItems()
      .then((items) => {
        setQuestionGovernance(items.length > 0 ? items : fallbackQuestionGovernance);
        setQuestionGovernanceStatus(null);
      })
      .catch(() => setQuestionGovernanceStatus('Mode demo : connectez-vous avec un role admin pour gouverner la banque de questions API.'));
    getInstitutionalAuthorizations()
      .then((items) => {
        setInstitutionalAuthorizations(items.length > 0 ? items : fallbackInstitutionalAuthorizations);
        setAuthorizationStatus(null);
      })
      .catch(() => setAuthorizationStatus('Mode demo : connectez-vous avec un role admin pour charger les habilitations API.'));
    getAuditLogs()
      .then((logs) => {
        setAuditLogs(logs);
        setAuditStatus(null);
      })
      .catch(() => setAuditStatus('Logs indisponibles : connectez-vous avec un role admin ou super admin.'));
  }, []);

  async function refreshAuditLogs() {
    try {
      setAuditLogs(await getAuditLogs());
    } catch {
      setAuditStatus('Logs indisponibles : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleCenterStatus(centerId: string, status: string, reason: string) {
    setCenterStatus(null);
    try {
      const updatedCenter = await updateCenterStatus(centerId, status, reason);
      setCenters((current) => current.map((center) => (center.id === centerId ? updatedCenter : center)));
      setCenterStatus(`Statut du centre ${updatedCenter.code} mis a jour : ${updatedCenter.status}.`);
      await refreshAuditLogs();
      getDashboard().then(setDashboard).catch(() => undefined);
    } catch {
      setCenterStatus('Mise a jour du centre impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleIdentityDecision(checkId: string, status: string, reason: string) {
    setIdentityStatus(null);
    try {
      const updatedCheck = await decideCandidateIdentity(checkId, status, reason);
      setIdentityChecks((current) => current.map((check) => (check.id === checkId ? updatedCheck : check)));
      setIdentityStatus(`Verification identite ${updatedCheck.document_reference} : ${updatedCheck.status}.`);
      await refreshAuditLogs();
    } catch {
      setIdentityStatus('Decision identite impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleQuestionDecision(questionId: string, status: string, reason: string) {
    setQuestionGovernanceStatus(null);
    try {
      const updatedItem = await decideQuestionGovernance(questionId, status, reason);
      setQuestionGovernance((current) => current.map((item) => (item.question_id === questionId ? updatedItem : item)));
      setQuestionGovernanceStatus(`Question ${updatedItem.category} : ${updatedItem.latest_status}.`);
      await refreshAuditLogs();
      getDashboard().then(setDashboard).catch(() => undefined);
    } catch {
      setQuestionGovernanceStatus('Decision question impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleAuthorizationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthorizationStatus(null);
    try {
      const created = await createInstitutionalAuthorization(authorizationForm);
      setInstitutionalAuthorizations((current) => [created, ...current]);
      setAuthorizationStatus(`Habilitation ${created.reference} creee en statut ${created.status}.`);
      await refreshAuditLogs();
    } catch {
      setAuthorizationStatus('Creation habilitation impossible : verifiez la reference et le role admin.');
    }
  }

  async function handleAuthorizationStatus(authorizationId: string, status: string, reason: string) {
    setAuthorizationStatus(null);
    try {
      const updated = await updateInstitutionalAuthorizationStatus(authorizationId, status, reason);
      setInstitutionalAuthorizations((current) => current.map((item) => (item.id === authorizationId ? updated : item)));
      setAuthorizationStatus(`Habilitation ${updated.reference} : ${updated.status}.`);
      await refreshAuditLogs();
    } catch {
      setAuthorizationStatus('Decision habilitation impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleDashboardCsvExport() {
    setIsExportingCsv(true);
    setCsvExportStatus(null);
    try {
      await downloadDashboardCsv();
      setCsvExportStatus('Export dashboard CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setCsvExportStatus('Export dashboard impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingCsv(false);
    }
  }

  async function handleExamAttemptsCsvExport() {
    setIsExportingExamCsv(true);
    setExamCsvExportStatus(null);
    try {
      await downloadExamAttemptsCsv();
      setExamCsvExportStatus('Export examens CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setExamCsvExportStatus('Export examens impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingExamCsv(false);
    }
  }

  async function handlePaymentCsvExport() {
    setIsExportingPaymentCsv(true);
    setPaymentCsvExportStatus(null);
    try {
      await downloadAdminPaymentsCsv(activePaymentFilters);
      setPaymentCsvExportStatus('Export paiements CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setPaymentCsvExportStatus('Export paiements impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingPaymentCsv(false);
    }
  }

  async function handlePaymentFiltersSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadPaymentSummary(paymentFilters);
    await refreshAuditLogs();
  }

  async function resetPaymentFilters() {
    setPaymentFilters({});
    await loadPaymentSummary({});
    await refreshAuditLogs();
  }

  const allowedEntries = entrySummary.by_result.allowed ?? 0;
  const deniedEntries = entrySummary.by_result.denied ?? 0;
  const centerRows = Object.entries(entrySummary.by_center).map(([center, values]) => [
    center,
    String(values.allowed ?? 0),
    String(values.denied ?? 0),
    buildRiskLabel(values.denied ?? 0),
  ]);
  const paymentProviderRows = Object.entries(paymentSummary.by_provider).map(([provider, values]) => [
    provider,
    String(values.count),
    formatCurrency(values.amount_gnf),
  ]);
  const paymentStatusRows = Object.entries(paymentSummary.by_status).map(([status, values]) => [
    status,
    String(values.count),
    formatCurrency(values.amount_gnf),
  ]);

  return (
    <section className="panel admin-panel">
      <p className="eyebrow dark">Administration nationale</p>
      <h2>Supervision centres, entrees, examens et finances</h2>
      <div className="actions result-actions admin-actions">
        <button onClick={handleDashboardCsvExport} disabled={isExportingCsv}>{isExportingCsv ? 'Export...' : 'Exporter le dashboard CSV'}</button>
        <button onClick={handleExamAttemptsCsvExport} disabled={isExportingExamCsv}>{isExportingExamCsv ? 'Export...' : 'Exporter les examens CSV'}</button>
        <button onClick={handlePaymentCsvExport} disabled={isExportingPaymentCsv}>{isExportingPaymentCsv ? 'Export...' : 'Exporter les paiements CSV'}</button>
      </div>
      {csvExportStatus && <p className="login-status">{csvExportStatus}</p>}
      {examCsvExportStatus && <p className="login-status">{examCsvExportStatus}</p>}
      {paymentCsvExportStatus && <p className="login-status">{paymentCsvExportStatus}</p>}
      {financeStatus && <p className="form-error">{financeStatus}</p>}
      <div className="metrics compact">
        <article><strong>{formatNumber(allowedEntries)}</strong><span>Entrees validees</span></article>
        <article><strong>{formatNumber(deniedEntries)}</strong><span>Entrees refusees</span></article>
        <article><strong>{formatNumber(examSummary.submitted_attempts)}</strong><span>Examens soumis</span></article>
        <article><strong>{formatNumber(examSummary.passed_attempts)}</strong><span>Reussites examen</span></article>
      </div>
      <div className="metrics compact">
        <article><strong>{formatNumber(examSummary.failed_attempts)}</strong><span>Echecs examen</span></article>
        <article><strong>{examSummary.average_score}</strong><span>Score moyen</span></article>
        <article><strong>{formatCurrency(paymentSummary.total_amount_gnf)}</strong><span>GNF encaisses</span></article>
        <article><strong>{formatNumber(paymentSummary.total_count)}</strong><span>Paiements</span></article>
      </div>
      <div className="center-governance-panel">
        <h3>Gouvernance des centres agrees</h3>
        <p>Suivi administratif des centres : audit initial, activation, accreditation et suspension.</p>
        {centerStatus && <p className={centerStatus.includes('impossible') ? 'form-error' : 'login-status'}>{centerStatus}</p>}
        <table>
          <thead><tr><th>Code</th><th>Centre</th><th>Ville</th><th>Capacite</th><th>Statut</th><th>Decision</th></tr></thead>
          <tbody>
            {centers.slice(0, 8).map((center) => (
              <tr key={center.id}>
                <td>{center.code}</td>
                <td>{center.name}</td>
                <td>{center.city}</td>
                <td>{center.capacity}</td>
                <td><span className="badge">{center.status}</span></td>
                <td>
                  <div className="table-actions">
                    <button onClick={() => handleCenterStatus(center.id, 'accredited', 'Accreditation institutionnelle validee')}>Accrediter</button>
                    <button onClick={() => handleCenterStatus(center.id, 'suspended', 'Suspension administrative pour controle')}>Suspendre</button>
                    <button onClick={() => handleCenterStatus(center.id, 'pending_audit', 'Retour en audit administratif')}>Audit</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="identity-panel">
        <h3>Verification identite candidat</h3>
        <p>Controle administratif des pieces avant convocation, entree en centre et emission des attestations.</p>
        {identityStatus && <p className={identityStatus.includes('impossible') || identityStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{identityStatus}</p>}
        <table>
          <thead><tr><th>Candidat</th><th>Document</th><th>Reference</th><th>Statut</th><th>Date</th><th>Decision</th></tr></thead>
          <tbody>
            {identityChecks.slice(0, 8).map((check) => (
              <tr key={check.id}>
                <td>{check.candidate_id}</td>
                <td>{check.document_type}</td>
                <td>{check.document_reference}</td>
                <td><span className={check.status === 'verified' ? 'badge ok' : 'badge'}>{check.status}</span></td>
                <td>{new Date(check.created_at).toLocaleString('fr-FR')}</td>
                <td>
                  <div className="table-actions">
                    <button onClick={() => handleIdentityDecision(check.id, 'verified', 'Piece conforme au controle administratif')}>Valider</button>
                    <button onClick={() => handleIdentityDecision(check.id, 'needs_review', 'Controle manuel complementaire requis')}>Revue</button>
                    <button onClick={() => handleIdentityDecision(check.id, 'rejected', 'Piece non conforme ou illisible')}>Rejeter</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="question-governance-panel">
        <h3>Banque nationale de questions</h3>
        <p>Publication, suspension et relecture officielle des questions utilisees dans les examens.</p>
        {questionGovernanceStatus && <p className={questionGovernanceStatus.includes('impossible') || questionGovernanceStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{questionGovernanceStatus}</p>}
        <table>
          <thead><tr><th>Categorie</th><th>Question</th><th>Statut</th><th>Active</th><th>Decision</th></tr></thead>
          <tbody>
            {questionGovernance.slice(0, 8).map((item) => (
              <tr key={item.question_id}>
                <td>{item.category}</td>
                <td>{item.text}</td>
                <td><span className={item.latest_status === 'published' ? 'badge ok' : 'badge'}>{item.latest_status}</span></td>
                <td>{item.is_active ? 'Oui' : 'Non'}</td>
                <td>
                  <div className="table-actions">
                    <button onClick={() => handleQuestionDecision(item.question_id, 'published', 'Question validee pour publication officielle')}>Publier</button>
                    <button onClick={() => handleQuestionDecision(item.question_id, 'needs_revision', 'Relecture pedagogique ou juridique requise')}>Relecture</button>
                    <button onClick={() => handleQuestionDecision(item.question_id, 'suspended', 'Question suspendue par decision administrative')}>Suspendre</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="authorization-panel">
        <h3>Habilitations institutionnelles</h3>
        <p>Registre des conventions, autorisations ministerielles et cadres de validite du dispositif.</p>
        {authorizationStatus && <p className={authorizationStatus.includes('impossible') || authorizationStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{authorizationStatus}</p>}
        <form className="authorization-form" onSubmit={handleAuthorizationSubmit}>
          <label>Autorite<input value={authorizationForm.authority} onChange={(event) => setAuthorizationForm((current) => ({ ...current, authority: event.target.value }))} /></label>
          <label>Reference<input value={authorizationForm.reference} onChange={(event) => setAuthorizationForm((current) => ({ ...current, reference: event.target.value }))} /></label>
          <label>Titre<input value={authorizationForm.title} onChange={(event) => setAuthorizationForm((current) => ({ ...current, title: event.target.value }))} /></label>
          <label>Perimetre<input value={authorizationForm.scope} onChange={(event) => setAuthorizationForm((current) => ({ ...current, scope: event.target.value }))} /></label>
          <button type="submit">Enregistrer habilitation</button>
        </form>
        <table>
          <thead><tr><th>Reference</th><th>Autorite</th><th>Titre</th><th>Statut</th><th>Validite</th><th>Decision</th></tr></thead>
          <tbody>
            {institutionalAuthorizations.slice(0, 8).map((item) => (
              <tr key={item.id}>
                <td>{item.reference}</td>
                <td>{item.authority}</td>
                <td>{item.title}</td>
                <td><span className={item.status === 'approved' ? 'badge ok' : 'badge'}>{item.status}</span></td>
                <td>{item.valid_until ? new Date(item.valid_until).toLocaleDateString('fr-FR') : 'A definir'}</td>
                <td>
                  <div className="table-actions">
                    <button onClick={() => handleAuthorizationStatus(item.id, 'approved', 'Habilitation approuvee par l autorite competente')}>Approuver</button>
                    <button onClick={() => handleAuthorizationStatus(item.id, 'pending_signature', 'Signature institutionnelle en attente')}>Signature</button>
                    <button onClick={() => handleAuthorizationStatus(item.id, 'revoked', 'Habilitation revoquee par decision administrative')}>Revoquer</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="institutional-panel">
        <div className="institutional-header">
          <div>
            <h3>Dossier institutionnel Etat guineen</h3>
            <p>{institutionalReadiness.summary}</p>
          </div>
          <strong>{institutionalReadiness.score}%</strong>
        </div>
        <span className="badge ok">{institutionalReadiness.label}</span>
        {readinessStatus && <p className="form-error">{readinessStatus}</p>}
        <div className="readiness-grid">
          {institutionalReadiness.items.map((item) => (
            <article key={item.pillar} className={`readiness-item status-${item.status}`}>
              <span>{item.status}</span>
              <strong>{item.pillar}</strong>
              <p>{item.evidence}</p>
              <small>{item.next_step}</small>
            </article>
          ))}
        </div>
      </div>
      <div className="finance-panel">
        <h3>Supervision financiere</h3>
        <form className="finance-filters" onSubmit={handlePaymentFiltersSubmit}>
          <label>Operateur
            <select value={paymentFilters.provider ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, provider: event.target.value || undefined }))}>
              <option value="">Tous</option>
              <option value="orange_money">Orange Money</option>
              <option value="mtn_money">MTN Money</option>
              <option value="sandbox">Sandbox</option>
            </select>
          </label>
          <label>Statut
            <select value={paymentFilters.status ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, status: event.target.value || undefined }))}>
              <option value="">Tous</option>
              <option value="paid">Paid</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          <label>Date debut<input type="datetime-local" value={paymentFilters.date_from ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, date_from: event.target.value || undefined }))} /></label>
          <label>Date fin<input type="datetime-local" value={paymentFilters.date_to ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, date_to: event.target.value || undefined }))} /></label>
          <button type="submit">Appliquer les filtres</button>
          <button type="button" className="secondary-button" onClick={resetPaymentFilters}>Reinitialiser</button>
        </form>
        <div className="finance-alerts-panel">
          <strong>Alertes financieres</strong>
          {paymentAlerts.length === 0 ? <p>Aucune alerte financiere sur le perimetre filtre.</p> : (
            <div className="alert-list">
              {paymentAlerts.slice(0, 8).map((alert) => (
                <article className={`finance-alert severity-${alert.severity}`} key={`${alert.type}-${alert.reference}-${alert.receipt_number}`}>
                  <span>{alert.severity}</span>
                  <strong>{alert.message}</strong>
                  <small>{alert.reference} - {alert.provider} - {formatCurrency(alert.amount_gnf)}</small>
                </article>
              ))}
            </div>
          )}
        </div>
        <div className="grid modules-grid">
          <div>
            <strong>Par operateur</strong>
            <table>
              <thead><tr><th>Operateur</th><th>Transactions</th><th>Montant</th></tr></thead>
              <tbody>{paymentProviderRows.map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody>
            </table>
          </div>
          <div>
            <strong>Par statut</strong>
            <table>
              <thead><tr><th>Statut</th><th>Transactions</th><th>Montant</th></tr></thead>
              <tbody>{paymentStatusRows.map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </div>
        <div className="payment-items-panel">
          <strong>Paiements recents filtres</strong>
          <table>
            <thead><tr><th>Reference</th><th>Reservation</th><th>Operateur</th><th>Statut</th><th>Montant</th><th>Recu</th><th>Date</th></tr></thead>
            <tbody>
              {paymentItems.map((payment) => (
                <tr key={payment.reference}>
                  <td>{payment.reference}</td>
                  <td>{payment.booking_reference}</td>
                  <td>{payment.provider}</td>
                  <td><span className="badge">{payment.status}</span></td>
                  <td>{formatCurrency(payment.amount_gnf)}</td>
                  <td>{payment.receipt_number}</td>
                  <td>{payment.created_at ? new Date(payment.created_at).toLocaleString('fr-FR') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <table>
        <thead><tr><th>Centre</th><th>Validees</th><th>Refusees</th><th>Risque</th></tr></thead>
        <tbody>
          {centerRows.map((row) => (
            <tr key={row[0]}>{row.map((cell, index) => <td key={`${row[0]}-${index}`}>{index === 3 ? <span className="badge">{cell}</span> : cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
      <div className="audit-panel">
        <h3>Journal d'audit national</h3>
        {auditStatus && <p className="form-error">{auditStatus}</p>}
        <table>
          <thead><tr><th>Date</th><th>Action</th><th>Entite</th><th>Details</th></tr></thead>
          <tbody>
            {auditLogs.slice(0, 8).map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.created_at).toLocaleString('fr-FR')}</td>
                <td><span className="badge">{log.action}</span></td>
                <td>{log.entity}</td>
                <td>{formatAuditDetails(log.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function ExamPage() {
  return (
    <section className="screen exam-screen">
      <div>
        <p className="eyebrow dark">Examen securise</p>
        <h2>Question 12 / 40</h2>
        <p>Mode centre agree avec surveillance, minuterie et trace d'audit de la tentative.</p>
        <p className="question">Que devez-vous faire face a un feu rouge fixe ?</p>
        <div className="answer selected">A. Marquer l'arret obligatoire</div>
        <div className="answer">B. Passer si la voie est libre</div>
        <div className="answer">C. Klaxonner puis avancer</div>
      </div>
      <aside className="timer-card"><span>Temps restant</span><strong>18:24</strong><p>Score requis : 35 / 40</p></aside>
    </section>
  );
}

export function ResultsPage() {
  const [examSummary, setExamSummary] = useState<ExamSummary>(fallbackExamSummary);
  const [attemptId, setAttemptId] = useState('');
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
      const result = await verifyExamCertificate(attemptId);
      setCertificateVerification(result);
    } catch {
      setCertificateError("Verification impossible. Verifiez que l'API est demarree.");
    } finally {
      setIsVerifyingCertificate(false);
    }
  }

  const score = 36;
  const total = 40;
  const threshold = 35;
  const passed = score >= threshold;
  const certificateUrl = attemptId ? getExamCertificatePdfUrl(attemptId) : null;
  return (
    <section className="screen two-columns">
      <div>
        <p className="eyebrow dark">Resultat candidat</p>
        <h2>Examen du code de la route</h2>
        <p>Le candidat consulte son score, son statut et les prochaines etapes apres correction automatique.</p>
        <div className="mini-card">Reference candidat : <strong>GN-CODE-2026-000001</strong></div>
        <div className="mini-card">Session : <strong>Centre Kaloum - 20/06/2026</strong></div>
        <div className="mini-card">Seuil de reussite : <strong>{threshold} / {total}</strong></div>
        <div className="mini-card">Score moyen national : <strong>{examSummary.average_score} / {total}</strong></div>
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
      </div>
      <div className="result-card">
        <span className={passed ? 'badge ok' : 'badge'}>{passed ? 'Admis' : 'Non admis'}</span>
        <strong>{score} / {total}</strong>
        <p>{passed ? 'Resultat positif. Certificat numerique pret pour validation administrative.' : 'Resultat insuffisant. Nouvelle presentation possible selon les regles nationales.'}</p>
        <div className="metrics compact">
          <article><strong>{formatNumber(examSummary.submitted_attempts)}</strong><span>Examens soumis</span></article>
          <article><strong>{formatNumber(examSummary.passed_attempts)}</strong><span>Admis</span></article>
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
