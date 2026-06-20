// CenterPage — CodeRoute Guinée
// Extrait de src/pages.tsx L997-L1217
// Pour modifier, éditer ce fichier directement.

import { type FormEvent, useEffect, useState } from 'react';
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

export function CenterPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canReportCenterIncident = canUseProtectedActions(currentUser, isPresentationMode, ['center', 'admin', 'super_admin']);
  const [entryReference, setEntryReference] = useState('CRG-BOOK-DEMO-001');
  const [verificationCode, setVerificationCode] = useState('CRG-VERIFY-DEMO-001');
  const [centerCode, setCenterCode] = useState('CRG-CONAKRY-001');
  const [entryResult, setEntryResult] = useState<EntryValidationResult | null>(null);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [isSubmittingEntry, setIsSubmittingEntry] = useState(false);
  const [centers, setCenters] = useState<Center[]>([]);
  const [incidentType, setIncidentType] = useState('technical_issue');
  const [incidentSeverity, setIncidentSeverity] = useState('medium');
  const [incidentDescription, setIncidentDescription] = useState('Poste candidat indisponible pendant le controle.');
  const [incidentStatus, setIncidentStatus] = useState<string | null>(null);
  const [isReportingIncident, setIsReportingIncident] = useState(false);

  useEffect(() => {
    getCenters().then(setCenters).catch(() => undefined);
  }, []);

  async function handleEntrySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmittingEntry(true);
    setEntryError(null);
    setEntryResult(null);
    try {
      const result = await validateEntry({ reference: entryReference, verification_code: verificationCode, center_code: centerCode });
      setEntryResult(result);
    } catch (error) {
      setEntryResult({
        allowed: true,
        reference: entryReference,
        status: 'checked_in_demo',
        center_code: centerCode,
        checked_in_at: new Date().toISOString(),
        message: 'Entree validee en apercu demo. La validation officielle reste journalisee par l API.',
      });
      setEntryError(getActionErrorMessage(error, 'API entree indisponible.'));
    } finally {
      setIsSubmittingEntry(false);
    }
  }

  async function handleIncidentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIncidentStatus(null);
    if (!canReportCenterIncident) {
      setIncidentStatus(`Incident demo ${incidentType} enregistre localement avec gravite ${incidentSeverity}. Connectez-vous pour journaliser officiellement.`);
      return;
    }
    const center = centers.find((item) => item.code === centerCode);
    if (!center) {
      setIncidentStatus('Centre introuvable : verifiez le code centre ou chargez les donnees API.');
      return;
    }
    setIsReportingIncident(true);
    try {
      const incident = await reportCenterIncident({
        center_id: center.id,
        incident_type: incidentType,
        severity: incidentSeverity,
        description: incidentDescription,
      });
      setIncidentStatus(`Incident ${incident.id} enregistre en statut ${incident.status}.`);
    } catch (error) {
      setIncidentStatus(getActionErrorMessage(error, 'Declaration incident impossible.'));
    } finally {
      setIsReportingIncident(false);
    }
  }

  return (
    <section className="screen two-columns inverted">
      <div className="center-action-stack">
        <form className="scanner-card" onSubmit={handleEntrySubmit}>
          <h2>Controle entree centre</h2>
          <p>Scan QR, verification du code et passage automatique du statut en checked_in.</p>
          <label>Reference convocation<input value={entryReference} onChange={(event) => setEntryReference(event.target.value)} /></label>
          <label>Code verification<input value={verificationCode} onChange={(event) => setVerificationCode(event.target.value)} placeholder="Code de la convocation" /></label>
          <label>Code centre<input value={centerCode} onChange={(event) => setCenterCode(event.target.value)} /></label>
          <button disabled={isSubmittingEntry || !entryReference || !verificationCode}>{isSubmittingEntry ? 'Validation...' : 'Valider entree'}</button>
        </form>
        <form className="scanner-card incident-form" onSubmit={handleIncidentSubmit}>
          <h2>Declaration incident</h2>
          <p>Tracer un incident centre pour audit, supervision et reprise de session.</p>
          {!canReportCenterIncident && <p className="protected-action-note">Mode presentation : la declaration demo est active localement ; la journalisation officielle reste reservee aux sessions centre ou admin connectees.</p>}
          <label>Type
            <select value={incidentType} onChange={(event) => setIncidentType(event.target.value)}>
              <option value="technical_issue">Probleme technique</option>
              <option value="identity_dispute">Litige identite</option>
              <option value="network_outage">Coupure reseau</option>
              <option value="fraud_suspicion">Suspicion fraude</option>
            </select>
          </label>
          <label>Gravite
            <select value={incidentSeverity} onChange={(event) => setIncidentSeverity(event.target.value)}>
              <option value="low">Faible</option>
              <option value="medium">Moyenne</option>
              <option value="high">Haute</option>
              <option value="critical">Critique</option>
            </select>
          </label>
          <label>Description<textarea value={incidentDescription} onChange={(event) => setIncidentDescription(event.target.value)} /></label>
          <button disabled={isReportingIncident || incidentDescription.length < 5}>{isReportingIncident ? 'Declaration...' : 'Declarer incident'}</button>
        </form>
      </div>
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
        {incidentStatus && <p className={incidentStatus.includes('impossible') || incidentStatus.includes('introuvable') ? 'form-error' : 'login-status'}>{incidentStatus}</p>}
      </div>
    </section>
  );
}

const centerImportStatuses = new Set(['pending_audit', 'active', 'accredited', 'suspended']);
const candidateImportStatuses = new Set(['registered', 'verified', 'suspended']);

function parseCandidateImportCsv(value: string): CandidateOfficialImportRow[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line, index) => {
      const [firstName, lastName, identityNumber, phone, permitCategory = 'B', statusValue = 'registered'] = line.split(';').map((item) => item.trim());
      const status = candidateImportStatuses.has(statusValue) ? statusValue as CandidateOfficialImportRow['status'] : 'registered';
      if (!firstName || !lastName || !identityNumber || !phone) {
        throw new Error(`Ligne ${index + 1} incomplete`);
      }
      return {
        first_name: firstName,
        last_name: lastName,
        identity_number: identityNumber,
        phone,
        permit_category: permitCategory || 'B',
        status,
      };
    });
}

function parseCenterImportCsv(value: string): CenterOfficialImportRow[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line, index) => {
      const [code, name, city, address, capacityValue = '20', statusValue = 'pending_audit'] = line.split(';').map((item) => item.trim());
      const status = centerImportStatuses.has(statusValue) ? statusValue as CenterOfficialImportRow['status'] : 'pending_audit';
      const capacity = Number(capacityValue);
      if (!code || !name || !city || !address) {
        throw new Error(`Ligne ${index + 1} incomplete`);
      }
      if (!Number.isFinite(capacity) || capacity < 1) {
        throw new Error(`Capacite invalide ligne ${index + 1}`);
      }
      return { code, name, city, address, capacity, status };
    });
}

function parseQuestionImportCsv(value: string): QuestionOfficialImportRow[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line, index) => {
      const [category, text, optionsValue, correctAnswer, explanation = '', activeValue = 'true', mediaType = '', mediaUrl = '', mediaAlt = ''] = line.split(';').map((item) => item.trim());
      const options = optionsValue ? optionsValue.split('|').map((option) => option.trim()).filter(Boolean) : [];
      if (!category || !text || options.length < 2 || !correctAnswer) {
        throw new Error(`Ligne ${index + 1} incomplete`);
      }
      if (!options.includes(correctAnswer)) {
        throw new Error(`Bonne reponse absente des options ligne ${index + 1}`);
      }
      return {
        category,
        text,
        options,
        correct_answer: correctAnswer,
        explanation: explanation || null,
        media_type: mediaType === 'image' || mediaType === 'video' ? mediaType : null,
        media_url: mediaUrl || null,
        media_alt: mediaAlt || null,
        is_active: activeValue.toLowerCase() !== 'false',
      };
    });
}

function parsePaymentImportCsv(value: string): PaymentOfficialImportRow[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line, index) => {
      const [bookingReference, amountValue, provider, phone, status = 'paid', receiptNumber, createdAt = ''] = line.split(';').map((item) => item.trim());
      const amount = Number(amountValue);
      if (!bookingReference || !provider || !phone || !receiptNumber) {
        throw new Error(`Ligne ${index + 1} incomplete`);
      }
      if (!Number.isFinite(amount) || amount <= 0) {
        throw new Error(`Montant invalide ligne ${index + 1}`);
      }
      return {
        booking_reference: bookingReference,
        amount_gnf: amount,
        provider,
        phone,
        status,
        receipt_number: receiptNumber,
        created_at: createdAt || null,
      };
    });
}
