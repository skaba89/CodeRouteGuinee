// CandidatePage — CodeRoute Guinée
// Extrait de src/pages.tsx L772-L996
// Pour modifier, éditer ce fichier directement.

import { type FormEvent, useState } from 'react';
import { type AuthUser } from '../authClient';
import { type UserRole } from '../auth';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import * as api from '../api';
import {
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
} from '../api';
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
} from './helpers';

export function CandidatePage() {
  const [bookingReference, setBookingReference] = useState('CRG-BOOK-DEMO-001');
  const [identityForm, setIdentityForm] = useState<CandidateIdentityPayload>({
    candidate_id: 'demo-candidate-1',
    document_type: 'national_id',
    document_reference: 'NINA-DEMO-001',
    photo_reference: 'photo-candidat-demo',
  });
  const [identitySubmission, setIdentitySubmission] = useState<CandidateIdentityCheck | null>(null);
  const [identitySubmissionStatus, setIdentitySubmissionStatus] = useState<string | null>(null);
  const [isSubmittingIdentity, setIsSubmittingIdentity] = useState(false);
  const [submissionForm, setSubmissionForm] = useState<CandidateSubmissionPayload>({
    candidate_id: 'demo-candidate-1',
    attempt_id: 'demo-attempt-1',
    category: 'review',
    message: 'Je souhaite que mon dossier soit examine par l administration.',
  });
  const [candidateSubmission, setCandidateSubmission] = useState<CandidateSubmission | null>(null);
  const [candidateSubmissionStatus, setCandidateSubmissionStatus] = useState<string | null>(null);
  const [isSubmittingFollowup, setIsSubmittingFollowup] = useState(false);
  const [amount, setAmount] = useState(250000);
  const [provider, setProvider] = useState('orange_money');
  const [phone, setPhone] = useState('+224622000000');
  const [paymentResult, setPaymentResult] = useState<PaymentResult | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);
  const convocationUrl = getConvocationPdfUrl(bookingReference);
  const candidateSteps = [
    ['Identite', 'Validee', 'Piece nationale controlee avant reservation'],
    ['Reservation', 'Confirmee', 'Centre Kaloum - 20/06/2026'],
    ['Paiement', paymentResult?.status ?? 'En attente', paymentResult ? 'Recu mobile money genere' : 'Paiement requis pour verrouiller la place'],
    ['Convocation', paymentResult ? 'Disponible' : 'Prete apres paiement', 'PDF avec QR code et code de verification'],
  ];
  const candidateDocuments = [
    ['Reference candidat', 'GN-CODE-2026-000001'],
    ['Categorie permis', 'B - Vehicule leger'],
    ['Centre', 'CTR-KALOUM'],
    ['Poste prevu', 'Affectation le jour J'],
  ];
  const preparationItems = [
    'Verifier la piece d identite originale',
    'Arriver 30 minutes avant la session',
    'Presenter la convocation QR au centre',
    'Relire les categories signalisation et priorite',
  ];

  async function handlePaymentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPaying(true);
    setPaymentError(null);
    setPaymentResult(null);
    try {
      const result = await createPayment({ booking_reference: bookingReference, amount_gnf: amount, provider, phone });
      setPaymentResult(result);
    } catch (error) {
      setPaymentResult({
        reference: 'GN-PAY-DEMO-001',
        booking_reference: bookingReference,
        amount_gnf: amount,
        provider,
        status: 'paid',
        receipt_number: `DEMO-${Date.now().toString().slice(-6)}`,
        message: 'Paiement demo confirme localement.',
      });
      setPaymentError(`${getActionErrorMessage(error, 'API paiement indisponible.')} Paiement demo confirme localement.`);
    } finally {
      setIsPaying(false);
    }
  }

  async function handleIdentitySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIdentitySubmissionStatus(null);
    setIdentitySubmission(null);
    setIsSubmittingIdentity(true);
    try {
      const created = await submitCandidateIdentity(identityForm);
      setIdentitySubmission(created);
      setIdentitySubmissionStatus(`Piece ${created.document_reference} deposee en statut ${created.status}.`);
    } catch (error) {
      const created: CandidateIdentityCheck = {
        id: `demo-identity-${Date.now().toString().slice(-6)}`,
        candidate_id: identityForm.candidate_id,
        document_type: identityForm.document_type,
        document_reference: identityForm.document_reference,
        photo_reference: identityForm.photo_reference,
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      setIdentitySubmission(created);
      setIdentitySubmissionStatus(`${getActionErrorMessage(error, 'API identite indisponible.')} Piece enregistree en apercu demo.`);
    } finally {
      setIsSubmittingIdentity(false);
    }
  }

  async function handleCandidateSubmissionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCandidateSubmissionStatus(null);
    setCandidateSubmission(null);
    setIsSubmittingFollowup(true);
    try {
      const created = await submitCandidateSubmission(submissionForm);
      setCandidateSubmission(created);
      setCandidateSubmissionStatus(`Recours ${created.id} depose en statut ${created.status}.`);
    } catch (error) {
      const created: CandidateSubmission = {
        id: `demo-recours-${Date.now().toString().slice(-6)}`,
        candidate_id: submissionForm.candidate_id,
        attempt_id: submissionForm.attempt_id,
        category: submissionForm.category,
        status: 'submitted',
        message: submissionForm.message,
        created_at: new Date().toISOString(),
      };
      setCandidateSubmission(created);
      setCandidateSubmissionStatus(`${getActionErrorMessage(error, 'API recours indisponible.')} Recours cree en apercu demo.`);
    } finally {
      setIsSubmittingFollowup(false);
    }
  }

  return (
    <section className="screen candidate-workspace">
      <div className="candidate-main">
        <div className="candidate-header">
          <div>
            <p className="eyebrow dark">Espace candidat</p>
            <h2>Dossier, reservation et convocation</h2>
            <p>Le candidat suit son dossier, reserve une session, paie et telecharge sa convocation PDF avec QR code.</p>
          </div>
          <span className="badge ok">Dossier recevable</span>
        </div>
        <div className="candidate-step-grid">
          {candidateSteps.map(([label, status, detail]) => (
            <article key={label}>
              <span>{label}</span>
              <strong>{status}</strong>
              <p>{detail}</p>
            </article>
          ))}
        </div>
        <div className="candidate-document-grid">
          {candidateDocuments.map(([label, value]) => (
            <div className="mini-card" key={label}>{label} : <strong>{value}</strong></div>
          ))}
        </div>
        <form className="candidate-document-form" onSubmit={handleIdentitySubmit}>
          <h2>Pieces justificatives</h2>
          <p>Depot d une piece pour controle administratif avant convocation et passage en centre.</p>
          <label>ID candidat<input value={identityForm.candidate_id} onChange={(event) => setIdentityForm((current) => ({ ...current, candidate_id: event.target.value }))} /></label>
          <label>Type de piece
            <select value={identityForm.document_type} onChange={(event) => setIdentityForm((current) => ({ ...current, document_type: event.target.value }))}>
              <option value="national_id">Carte nationale</option>
              <option value="passport">Passeport</option>
              <option value="driver_file">Dossier auto-ecole</option>
            </select>
          </label>
          <label>Reference piece<input value={identityForm.document_reference} onChange={(event) => setIdentityForm((current) => ({ ...current, document_reference: event.target.value }))} /></label>
          <label>Reference photo<input value={identityForm.photo_reference ?? ''} onChange={(event) => setIdentityForm((current) => ({ ...current, photo_reference: event.target.value }))} /></label>
          <button disabled={isSubmittingIdentity || identityForm.candidate_id.length < 3 || identityForm.document_reference.length < 3}>{isSubmittingIdentity ? 'Depot...' : 'Deposer la piece'}</button>
        </form>
        {identitySubmissionStatus && <p className={identitySubmissionStatus.includes('impossible') ? 'form-error' : 'login-status'}>{identitySubmissionStatus}</p>}
        {identitySubmission && (
          <div className="candidate-identity-receipt">
            <strong>Controle cree : {identitySubmission.id}</strong>
            <span>Statut : {identitySubmission.status}</span>
            <span>Reference : {identitySubmission.document_reference}</span>
          </div>
        )}
        <form className="candidate-submission-form" onSubmit={handleCandidateSubmissionSubmit}>
          <h2>Recours et reclamations</h2>
          <p>Demande officielle de revue apres examen, incident ou contestation de dossier.</p>
          <label>ID candidat<input value={submissionForm.candidate_id} onChange={(event) => setSubmissionForm((current) => ({ ...current, candidate_id: event.target.value }))} /></label>
          <label>ID tentative<input value={submissionForm.attempt_id} onChange={(event) => setSubmissionForm((current) => ({ ...current, attempt_id: event.target.value }))} /></label>
          <label>Categorie
            <select value={submissionForm.category} onChange={(event) => setSubmissionForm((current) => ({ ...current, category: event.target.value }))}>
              <option value="review">Revue de dossier</option>
              <option value="appeal">Recours resultat</option>
              <option value="incident">Incident centre</option>
              <option value="correction">Correction administrative</option>
            </select>
          </label>
          <label>Message<textarea value={submissionForm.message} onChange={(event) => setSubmissionForm((current) => ({ ...current, message: event.target.value }))} /></label>
          <button disabled={isSubmittingFollowup || submissionForm.candidate_id.length < 3 || submissionForm.attempt_id.length < 3 || submissionForm.message.length < 10}>{isSubmittingFollowup ? 'Depot...' : 'Deposer le recours'}</button>
        </form>
        {candidateSubmissionStatus && <p className={candidateSubmissionStatus.includes('impossible') ? 'form-error' : 'login-status'}>{candidateSubmissionStatus}</p>}
        {candidateSubmission && (
          <div className="candidate-identity-receipt">
            <strong>Recours cree : {candidateSubmission.id}</strong>
            <span>Statut : {candidateSubmission.status}</span>
            <span>Categorie : {candidateSubmission.category}</span>
          </div>
        )}
        <form className="payment-form" onSubmit={handlePaymentSubmit}>
          <h2>Paiement Mobile Money</h2>
          <label>Reference reservation<input value={bookingReference} onChange={(event) => setBookingReference(event.target.value)} /></label>
          <label>Montant GNF<input type="number" value={amount} onChange={(event) => setAmount(Number(event.target.value))} /></label>
          <label>Operateur<input value={provider} onChange={(event) => setProvider(event.target.value)} /></label>
          <label>Telephone<input value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <button disabled={isPaying}>{isPaying ? 'Traitement...' : 'Payer maintenant'}</button>
        </form>
      </div>
      <aside className="qr-card candidate-side-card">
        <div className="qr-box" />
        <strong>Convocation verifiable</strong>
        <span>{bookingReference}</span>
        <a className="download-link" href={convocationUrl} target="_blank" rel="noreferrer">Telecharger la convocation PDF</a>
        <div className="candidate-prep-list">
          <strong>Avant la session</strong>
          {preparationItems.map((item) => <p key={item}>{item}</p>)}
        </div>
        {paymentResult && (
          <div className="payment-result">
            <strong>Recu : {paymentResult.receipt_number}</strong>
            <span>Reference : {paymentResult.reference}</span>
            <span>Statut : {paymentResult.status}</span>
          </div>
        )}
        {paymentError && <p className="form-error">{paymentError}</p>}
      </aside>
    </section>
  );
}
