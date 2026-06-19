// Helpers et types partagés entre toutes les pages CodeRoute Guinée
// Ce fichier est généré automatiquement depuis pages.tsx — ne pas modifier directement.
// Source : src/pages.tsx L1-L651

import { type FormEvent, useEffect, useState } from 'react';

import {
  type Center,
  type CenterIncident,
  type CenterOfficialImportRow,
  type CenterStation,
  type CenterStationPayload,
  type AuditLogEntry,
  type AuditLogFilters,
  type Candidate,
  type CandidateIdentityCheck,
  type CandidateIdentityFilters,
  type CandidateIdentityPayload,
  type CandidateOfficialImportRow,
  type CandidateSubmission,
  type CandidateSubmissionFilters,
  type CandidateSubmissionPayload,
  type DashboardData,
  type DeviceSession,
  type EntrySummary,
  type EntryValidationResult,
  type ExamAttempt,
  type ExamCertificateVerification,
  type ExamMonitoringEvent,
  type ExamMonitoringFilters,
  type ExamMonitoringSummary,
  type ExamQuestion,
  type ExamSummary,
  type InstitutionalAuthorization,
  type InstitutionalAuthorizationPayload,
  type InstitutionalActionCenter,
  type InstitutionalReport,
  type InstitutionalReadiness,
  type InstitutionalUser,
  type InstitutionalUserCreatePayload,
  type OperationalReadiness,
  type OperationsSummary,
  type PaymentAlert,
  type PaymentFilters,
  type PaymentOfficialImportRow,
  type PaymentReconciliationItem,
  type PaymentResult,
  type PaymentSummary,
  type QuestionGovernanceItem,
  type QuestionOfficialImportRow,
  createInstitutionalAuthorization,
  createInstitutionalUser,
  createCenterStation,
  createPayment,
  decideCandidateIdentity,
  decideQuestionGovernance,
  downloadAuditLogsCsv,
  downloadAdminPaymentsCsv,
  downloadDashboardCsv,
  downloadExamAttemptsCsv,
  downloadInstitutionalReportCsv,
  downloadInstitutionalReportPdf,
  getAdminPaymentSummary,
  getAuditLogs,
  getCandidateIdentityChecks,
  getCandidateSubmissions,
  getCandidates,
  getCenters,
  getCenterStations,
  getCenterIncidents,
  getConvocationPdfUrl,
  getDashboard,
  getDeviceSessionAlerts,
  getEntrySummary,
  getExamCertificatePdfUrl,
  getExamMonitoringEvents,
  getExamMonitoringSummaries,
  getExamSummary,
  getQuestions,
  getInstitutionalActionCenter,
  getInstitutionalReport,
  getInstitutionalReadiness,
  getInstitutionalAuthorizations,
  getInstitutionalUsers,
  getOperationalReadiness,
  getOperationsSummary,
  getPaymentAlerts,
  getPaymentReconciliationItems,
  getQuestionGovernanceItems,
  handleCandidateSubmission,
  importOfficialCandidates,
  importOfficialCenters,
  importOfficialPayments,
  importOfficialQuestions,
  resetInstitutionalUserPassword,
  reportCenterIncident,
  resolveCenterIncident,
  startExamFromBooking,
  submitCandidateIdentity,
  submitCandidateSubmission,
  submitExamAttempt,
  validateEntry,
  updateCenterStatus,
  updateCenterStation,
  updateInstitutionalAuthorizationStatus,
  updateInstitutionalUserRole,
  updateInstitutionalUserStatus,
  verifyExamCertificate,
} from './api';
import { canUseProtectedActions, useAuthSession } from './authSession';

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

const fallbackOperationalReadiness: OperationalReadiness = {
  status: 'degraded',
  service: 'CodeRoute Guinee API',
  checks: {},
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

const fallbackInstitutionalReport: InstitutionalReport = {
  generated_for: 'Etat guineen - dossier CodeRoute Guinee',
  readiness_score: 70,
  readiness_label: 'Mode demonstration - pilote a renforcer',
  candidates: 1250,
  centers_by_status: { accredited: 18, pending_audit: 3 },
  questions_by_status: { active: 40, needs_revision: 2 },
  identity_checks_by_status: { verified: 420, pending: 18 },
  authorizations_by_status: { approved: 1, pending_signature: 1 },
  audit_events: 96,
  recommendations: [
    'Valider la nomenclature officielle des centres agrees avec l administration.',
    'Importer la banque officielle de questions par categorie de permis.',
  ],
};

const fallbackInstitutionalActionCenter: InstitutionalActionCenter = {
  total_actions: 8,
  critical_actions: 0,
  items: [
    { code: 'identity_checks', label: 'Identites candidates a traiter', count: 3, severity: 'warning', target: '#identites' },
    { code: 'authorizations_signature', label: 'Habilitations en attente de signature', count: 2, severity: 'warning', target: '#habilitations' },
    { code: 'question_revision', label: 'Questions officielles a relire', count: 3, severity: 'warning', target: '#questions' },
  ],
};

const fallbackOperationsSummary: OperationsSummary = {
  status: 'warning',
  generated_at: new Date().toISOString(),
  critical_alerts: 0,
  warning_alerts: 3,
  open_incidents: 2,
  critical_incidents: 0,
  high_risk_exam_events: 4,
  critical_exam_events: 0,
  suspicious_devices: 1,
  payment_alerts: 2,
  audit_events_24h: 12,
  last_audit_at: new Date().toISOString(),
  alerts: [
    { code: 'open_incidents', label: 'Incidents centre ouverts', severity: 'warning', count: 2, target: '#incidents' },
    { code: 'high_risk_exam_events', label: 'Evenements examen a risque eleve', severity: 'warning', count: 4, target: '#monitoring-examen' },
    { code: 'payment_alerts', label: 'Alertes financieres a traiter', severity: 'warning', count: 2, target: '#finance' },
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

const fallbackInstitutionalUsers: InstitutionalUser[] = [
  {
    id: 'demo-user-1',
    email: 'admin@coderoute.gov.gn',
    full_name: 'Administrateur National CodeRoute',
    role: 'super_admin',
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: 'demo-user-2',
    email: 'centre.kaloum@coderoute.gov.gn',
    full_name: 'Responsable Centre Kaloum',
    role: 'center',
    is_active: true,
    created_at: new Date().toISOString(),
  },
];

const fallbackCandidateSubmissions: CandidateSubmission[] = [
  {
    id: 'demo-submission-1',
    candidate_id: 'GN-CODE-2026-000001',
    attempt_id: 'demo-attempt-1',
    category: 'review',
    status: 'submitted',
    message: 'Demande de revue apres incident de poste en centre.',
    created_at: new Date().toISOString(),
  },
  {
    id: 'demo-submission-2',
    candidate_id: 'GN-CODE-2026-000002',
    attempt_id: 'demo-attempt-2',
    category: 'complaint',
    status: 'under_review',
    message: 'Contestations des conditions de passage.',
    admin_response: 'Analyse en cours par la supervision nationale.',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
];

const fallbackCenterIncidents: CenterIncident[] = [
  {
    id: 'demo-incident-1',
    center_id: 'CTR-KALOUM',
    session_id: 'GN-SESSION-DEMO-001',
    attempt_id: 'demo-attempt-1',
    incident_type: 'device_failure',
    severity: 'high',
    description: 'Poste indisponible pendant la tentative, reprise a arbitrer.',
    status: 'open',
    created_at: new Date().toISOString(),
  },
];

const fallbackPaymentItems: PaymentReconciliationItem[] = [
  {
    reference: 'GN-PAY-DEMO-001',
    booking_reference: 'GN-BOOK-2026-000001',
    amount_gnf: 250000,
    provider: 'orange_money',
    status: 'paid',
    receipt_number: 'OM-DEMO-001',
    created_at: new Date().toISOString(),
  },
  {
    reference: 'GN-PAY-DEMO-002',
    booking_reference: 'GN-BOOK-2026-000002',
    amount_gnf: 250000,
    provider: 'mtn_money',
    status: 'pending',
    receipt_number: 'MTN-DEMO-002',
    created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
  },
];

const fallbackPaymentAlerts: PaymentAlert[] = [
  {
    ...fallbackPaymentItems[1],
    type: 'pending_reconciliation',
    severity: 'medium',
    message: 'Paiement en attente de rapprochement operateur.',
  },
];

const fallbackMonitoringSummaries: ExamMonitoringSummary[] = [
  {
    attempt_id: 'demo-attempt-1',
    total_events: 3,
    total_risk_score: 7,
    max_severity: 'high',
    status: 'review_required',
  },
];

const fallbackMonitoringEvents: ExamMonitoringEvent[] = [
  {
    id: 'demo-monitoring-event-1',
    center_id: 'CTR-KALOUM',
    session_id: 'GN-SESSION-DEMO-001',
    attempt_id: 'demo-attempt-1',
    event_type: 'window_blur',
    severity: 'high',
    risk_score: 4,
    details: { source: 'presentation' },
    occurred_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
  },
  {
    id: 'demo-monitoring-event-2',
    center_id: 'CTR-KALOUM',
    session_id: 'GN-SESSION-DEMO-001',
    attempt_id: 'demo-attempt-1',
    event_type: 'unknown_device',
    severity: 'medium',
    risk_score: 3,
    details: { source: 'presentation' },
    occurred_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
  },
];

const fallbackDeviceSessionAlerts: DeviceSession[] = [
  {
    id: 'demo-device-alert-1',
    center_id: 'CTR-KALOUM',
    session_id: 'GN-SESSION-DEMO-001',
    attempt_id: 'demo-attempt-1',
    device_key: 'unknown-device-demo',
    device_label: 'Poste non enregistre',
    status: 'suspicious',
    risk_reason: 'Appareil absent du registre centre',
    created_at: new Date().toISOString(),
    last_seen_at: new Date().toISOString(),
  },
];

const fallbackAuditLogs: AuditLogEntry[] = [
  {
    id: 'demo-audit-1',
    action: 'dashboard.institutional_report_viewed',
    entity: 'dashboard',
    details: { mode: 'presentation' },
    created_at: new Date().toISOString(),
  },
  {
    id: 'demo-audit-2',
    action: 'candidate.official_import',
    entity: 'candidate',
    details: { dry_run: true, imported: 1 },
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  },
  {
    id: 'demo-audit-3',
    action: 'payments.official_import',
    entity: 'payment',
    details: { dry_run: true, imported: 1 },
    created_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
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

const dossierHighlights = [
  ['Objectif public', 'Digitaliser et harmoniser les examens du code de la route sous pilotage national.'],
  ['Benefices attendus', 'Reduire les files, fiabiliser les resultats, limiter les fraudes et produire du reporting.'],
  ['Preuves disponibles', 'Audit, exports CSV, certificats, controle centre, paiements, habilitations et readiness.'],
  ['Decision attendue', 'Valider un pilote institutionnel encadre avant extension progressive.'],
];

const dossierWorkstreams = [
  ['Gouvernance', 'Ministere, direction nationale, centres agrees, roles et habilitations.'],
  ['Parcours candidat', 'Dossier, reservation, paiement, convocation, examen, resultats et attestation.'],
  ['Controle centre', 'Validation entree, session, poste, supervision et incidents.'],
  ['Reporting national', 'Indicateurs, audit, finances, exports et maturite institutionnelle.'],
];

const dossierRisks = [
  ['Donnees officielles', 'Registres candidats, pieces identite et centres agrees doivent etre branches.'],
  ['Antifraude', 'Photo candidat, surveillance centre et detection anomalies restent a renforcer.'],
  ['Production', 'CI/CD, sauvegardes, monitoring, secrets et procedures exploitation sont requis.'],
];

export const DEMO_EXAM_ATTEMPT_STORAGE_KEY = 'coderoute-demo-exam-attempt-id';

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('fr-FR').format(value);
}

export function formatCurrency(value: number): string {
  return `${formatNumber(value)} GNF`;
}

export function buildRiskLabel(denied: number): string {
  if (denied >= 10) return 'A verifier';
  if (denied >= 4) return 'Audit';
  return 'Normal';
}

export function formatAuditDetails(details?: AuditLogEntry['details']): string {
  if (!details) return 'Aucun detail';
  const entries = Object.entries(details).slice(0, 3);
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(' | ');
}

export function sanitizePaymentFilters(filters: PaymentFilters): PaymentFilters {
  return {
    provider: filters.provider || undefined,
    status: filters.status || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  };
}

export function downloadLocalFile(filename: string, content: string, type = 'text/csv;charset=utf-8'): void {
  const blob = new Blob([content], { type });
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

export function buildDemoImportStatus(label: string, count: number): string {
  return `Simulation ${label} terminee : ${count} ligne(s) validee(s), aucune donnee officielle ecrite.`;
}

export function buildDemoExamAttempt(status: 'started' | 'submitted' = 'started'): ExamAttempt {
  return {
    id: 'demo-attempt-1',
    candidate_id: 'GN-CODE-2026-000001',
    session_id: 'GN-SESSION-DEMO-001',
    status,
    answers: status === 'submitted' ? { demo: 'submitted' } : null,
    score: status === 'submitted' ? 36 : null,
    passed: status === 'submitted' ? true : null,
    started_at: new Date().toISOString(),
    submitted_at: status === 'submitted' ? new Date().toISOString() : null,
  };
}

export function buildDemoCertificateVerification(attemptId: string): ExamCertificateVerification {
  return {
    valid: true,
    attempt_id: attemptId,
    status: 'submitted',
    candidate_reference: 'GN-CODE-2026-000001',
    candidate_name: 'Aissatou Camara',
    identity_number: 'NINA-DEMO-001',
    permit_category: 'B',
    session_reference: 'GN-SESSION-DEMO-001',
    center_name: 'Centre Kaloum',
    center_city: 'Conakry',
    score: 36,
    passed: true,
    submitted_at: new Date().toISOString(),
  };
}

export function buildDemoQuestionImage(label: string, color = '#1f7a4d'): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540"><rect width="960" height="540" fill="#eef5f1"/><path d="M0 430h960v110H0z" fill="#263238"/><path d="M0 485h960" stroke="#f4d03f" stroke-width="12" stroke-dasharray="48 32"/><circle cx="480" cy="215" r="96" fill="${color}"/><rect x="452" y="112" width="56" height="210" rx="10" fill="#fff"/><rect x="375" y="187" width="210" height="56" rx="10" fill="#fff"/><text x="480" y="72" text-anchor="middle" font-family="Arial" font-size="34" font-weight="700" fill="#18332a">${label}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function filterDemoIdentityChecks(filters: CandidateIdentityFilters): CandidateIdentityCheck[] {
  return fallbackIdentityChecks.filter((item) => {
    const statusMatches = !filters.status_filter || item.status === filters.status_filter;
    const candidateMatches = !filters.candidate_id || item.candidate_id.toLowerCase().includes(filters.candidate_id.toLowerCase());
    return statusMatches && candidateMatches;
  }).slice(0, filters.limit ?? 25);
}

export function filterDemoSubmissions(filters: CandidateSubmissionFilters): CandidateSubmission[] {
  return fallbackCandidateSubmissions.filter((item) => {
    const statusMatches = !filters.status_filter || item.status === filters.status_filter;
    const candidateMatches = !filters.candidate_id || item.candidate_id.toLowerCase().includes(filters.candidate_id.toLowerCase());
    const attemptMatches = !filters.attempt_id || item.attempt_id.toLowerCase().includes(filters.attempt_id.toLowerCase());
    return statusMatches && candidateMatches && attemptMatches;
  }).slice(0, filters.limit ?? 25);
}

export function filterDemoAuditLogs(filters: AuditLogFilters): AuditLogEntry[] {
  return fallbackAuditLogs.filter((item) => {
    const actionMatches = !filters.action || item.action.toLowerCase().includes(filters.action.toLowerCase());
    const entityMatches = !filters.entity || item.entity.toLowerCase().includes(filters.entity.toLowerCase());
    return actionMatches && entityMatches;
  }).slice(0, filters.limit ?? 25);
}

export function filterDemoMonitoring(filters: ExamMonitoringFilters): {
  summaries: ExamMonitoringSummary[];
  events: ExamMonitoringEvent[];
  deviceAlerts: DeviceSession[];
} {
  const events = fallbackMonitoringEvents.filter((item) => {
    const attemptMatches = !filters.attempt_id || item.attempt_id.toLowerCase().includes(filters.attempt_id.toLowerCase());
    const sessionMatches = !filters.session_id || item.session_id.toLowerCase().includes(filters.session_id.toLowerCase());
    const severityMatches = !filters.severity || item.severity === filters.severity;
    const riskMatches = item.risk_score >= (filters.min_risk_score ?? 1);
    return attemptMatches && sessionMatches && severityMatches && riskMatches;
  }).slice(0, filters.limit ?? 25);
  const attemptIds = new Set(events.map((item) => item.attempt_id));
  return {
    summaries: fallbackMonitoringSummaries.filter((item) => attemptIds.has(item.attempt_id)),
    events,
    deviceAlerts: fallbackDeviceSessionAlerts.filter((item) => !filters.session_id || item.session_id === filters.session_id),
  };
}

export function filterDemoPayments(filters: PaymentFilters): {
  summary: PaymentSummary;
  items: PaymentReconciliationItem[];
  alerts: PaymentAlert[];
} {
  const items = fallbackPaymentItems.filter((item) => {
    const providerMatches = !filters.provider || item.provider === filters.provider;
    const statusMatches = !filters.status || item.status === filters.status;
    return providerMatches && statusMatches;
  }).slice(0, filters.limit ?? 25);
  const summary: PaymentSummary = {
    total_count: items.length,
    total_amount_gnf: items.reduce((sum, item) => sum + item.amount_gnf, 0),
    by_status: {},
    by_provider: {},
  };
  items.forEach((item) => {
    summary.by_status[item.status] = summary.by_status[item.status] ?? { count: 0, amount_gnf: 0 };
    summary.by_status[item.status].count += 1;
    summary.by_status[item.status].amount_gnf += item.amount_gnf;
    summary.by_provider[item.provider] = summary.by_provider[item.provider] ?? { count: 0, amount_gnf: 0 };
    summary.by_provider[item.provider].count += 1;
    summary.by_provider[item.provider].amount_gnf += item.amount_gnf;
  });
  return {
    summary,
    items,
    alerts: fallbackPaymentAlerts.filter((alert) => items.some((item) => item.reference === alert.reference)),
  };
}

export function getActionErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

