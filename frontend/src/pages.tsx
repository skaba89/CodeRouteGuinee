import { type FormEvent, useEffect, useState } from 'react';

import {
  type DashboardData,
  type EntrySummary,
  type EntryValidationResult,
  type ExamCertificateVerification,
  type ExamSummary,
  type PaymentResult,
  createPayment,
  getConvocationPdfUrl,
  getDashboard,
  getEntrySummary,
  getExamCertificatePdfUrl,
  getExamSummary,
  validateEntry,
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

function buildRiskLabel(denied: number): string {
  if (denied >= 10) return 'A verifier';
  if (denied >= 4) return 'Audit';
  return 'Normal';
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
  const [entrySummary, setEntrySummary] = useState<EntrySummary>(fallbackEntrySummary);
  const [examSummary, setExamSummary] = useState<ExamSummary>(fallbackExamSummary);

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => undefined);
    getEntrySummary().then(setEntrySummary).catch(() => undefined);
    getExamSummary().then(setExamSummary).catch(() => undefined);
  }, []);

  const allowedEntries = entrySummary.by_result.allowed ?? 0;
  const deniedEntries = entrySummary.by_result.denied ?? 0;
  const centerRows = Object.entries(entrySummary.by_center).map(([center, values]) => [
    center,
    String(values.allowed ?? 0),
    String(values.denied ?? 0),
    buildRiskLabel(values.denied ?? 0),
  ]);

  return (
    <section className="panel admin-panel">
      <p className="eyebrow dark">Administration nationale</p>
      <h2>Supervision centres, entrees et examens</h2>
      <div className="metrics compact">
        <article><strong>{formatNumber(allowedEntries)}</strong><span>Entrees validees</span></article>
        <article><strong>{formatNumber(deniedEntries)}</strong><span>Entrees refusees</span></article>
        <article><strong>{formatNumber(examSummary.submitted_attempts)}</strong><span>Examens soumis</span></article>
        <article><strong>{formatNumber(examSummary.passed_attempts)}</strong><span>Reussites examen</span></article>
      </div>
      <div className="metrics compact">
        <article><strong>{formatNumber(examSummary.failed_attempts)}</strong><span>Echecs examen</span></article>
        <article><strong>{examSummary.average_score}</strong><span>Score moyen</span></article>
        <article><strong>58.5M</strong><span>GNF encaisses</span></article>
        <article><strong>{formatNumber(dashboard.fraud_alerts)}</strong><span>Alertes centre</span></article>
      </div>
      <table>
        <thead><tr><th>Centre</th><th>Validees</th><th>Refusees</th><th>Risque</th></tr></thead>
        <tbody>
          {centerRows.map((row) => (
            <tr key={row[0]}>{row.map((cell, index) => <td key={`${row[0]}-${index}`}>{index === 3 ? <span className="badge">{cell}</span> : cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function ExamPage() {
  return (
    <section className="screen exam-screen">
      <div>
        <p className="eyebrow dark">Interface examen</p>
        <h2>Question 12 / 40</h2>
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