import { getAuthHeaders } from './authClient';

export type DashboardData = {
  candidates: number;
  accredited_centers: number;
  exam_sessions: number;
  questions: number;
  fraud_alerts: number;
};

export type Center = {
  id: string;
  code: string;
  name: string;
  city: string;
  address: string;
  capacity: number;
  status: string;
  created_at: string;
};

export type OperationalReadiness = {
  status: 'ready' | 'degraded' | string;
  service: string;
  checks: Record<string, { status: string; detail?: string; version?: string | null }>;
};

export type EntrySummary = {
  total: number;
  by_result: Record<string, number>;
  by_center: Record<string, { allowed: number; denied: number }>;
};

export type ExamSummary = {
  total_attempts: number;
  submitted_attempts: number;
  passed_attempts: number;
  failed_attempts: number;
  average_score: number;
};

export type AuditLogEntry = {
  id: string;
  actor_id?: string;
  action: string;
  entity: string;
  entity_id?: string;
  details?: Record<string, string | number | boolean | null>;
  created_at: string;
};

export type PaymentSummaryBucket = {
  count: number;
  amount_gnf: number;
};

export type PaymentSummary = {
  total_count: number;
  total_amount_gnf: number;
  by_status: Record<string, PaymentSummaryBucket>;
  by_provider: Record<string, PaymentSummaryBucket>;
};

export type PaymentFilters = {
  provider?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
};

export type PaymentReconciliationItem = {
  reference: string;
  booking_reference: string;
  amount_gnf: number;
  provider: string;
  status: string;
  receipt_number: string;
  created_at?: string | null;
};

export type PaymentAlert = PaymentReconciliationItem & {
  type: string;
  severity: 'low' | 'medium' | 'high' | string;
  message: string;
};

export type AuditLogFilters = {
  action?: string;
  entity?: string;
  limit?: number;
};

export type InstitutionalUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type InstitutionalUserCreatePayload = {
  email: string;
  full_name: string;
  initial_password: string;
  role: string;
  reason: string;
};

export type InstitutionalReadinessItem = {
  pillar: string;
  status: 'ready' | 'partial' | 'todo' | string;
  evidence: string;
  next_step: string;
};

export type InstitutionalReadiness = {
  score: number;
  label: string;
  summary: string;
  items: InstitutionalReadinessItem[];
};

export type InstitutionalReport = {
  generated_for: string;
  readiness_score: number;
  readiness_label: string;
  candidates: number;
  centers_by_status: Record<string, number>;
  questions_by_status: Record<string, number>;
  identity_checks_by_status: Record<string, number>;
  authorizations_by_status: Record<string, number>;
  audit_events: number;
  recommendations: string[];
};

export type InstitutionalActionItem = {
  code: string;
  label: string;
  count: number;
  severity: 'normal' | 'warning' | 'critical' | string;
  target: string;
};

export type InstitutionalActionCenter = {
  total_actions: number;
  critical_actions: number;
  items: InstitutionalActionItem[];
};

export type CandidateIdentityCheck = {
  id: string;
  candidate_id: string;
  document_type: string;
  document_reference: string;
  photo_reference?: string | null;
  status: string;
  verified_by_id?: string | null;
  decision_reason?: string | null;
  created_at: string;
  decided_at?: string | null;
};

export type QuestionGovernanceItem = {
  question_id: string;
  category: string;
  text: string;
  is_active: boolean;
  latest_status: string;
  latest_reason?: string | null;
  decided_by_id?: string | null;
  decided_at?: string | null;
};

export type InstitutionalAuthorization = {
  id: string;
  authority: string;
  reference: string;
  title: string;
  scope: string;
  status: string;
  valid_from?: string | null;
  valid_until?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type InstitutionalAuthorizationPayload = {
  authority: string;
  reference: string;
  title: string;
  scope: string;
  valid_from?: string;
  valid_until?: string;
};

export type ExamCertificateVerification = {
  valid: boolean;
  attempt_id: string;
  status: string;
  candidate_reference?: string;
  candidate_name?: string;
  identity_number?: string;
  permit_category?: string;
  session_reference?: string;
  center_name?: string;
  center_city?: string;
  score?: number;
  passed?: boolean;
  submitted_at?: string;
  reason?: string;
};

export type EntryValidationPayload = {
  reference: string;
  verification_code: string;
  center_code?: string;
};

export type EntryValidationResult = {
  allowed: boolean;
  reference: string;
  status: string;
  center_code?: string;
  checked_in_at?: string;
  message?: string;
  reason?: string;
};

export type PaymentPayload = {
  booking_reference: string;
  amount_gnf: number;
  provider: string;
  phone: string;
};

export type PaymentResult = {
  reference: string;
  booking_reference: string;
  amount_gnf: number;
  provider: string;
  status: string;
  receipt_number: string;
  external_reference?: string;
  message?: string;
};

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000');

function buildPaymentQuery(filters: PaymentFilters = {}): string {
  const query = new URLSearchParams();
  if (filters.provider) query.set('provider', filters.provider);
  if (filters.status) query.set('status', filters.status);
  if (filters.date_from) query.set('date_from', filters.date_from);
  if (filters.date_to) query.set('date_to', filters.date_to);
  if (filters.limit) query.set('limit', String(filters.limit));
  const queryString = query.toString();
  return queryString ? `?${queryString}` : '';
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function getPrivateJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: getAuthHeaders() });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function buildAuditQuery(filters: AuditLogFilters = {}): string {
  const query = new URLSearchParams();
  if (filters.action) query.set('action', filters.action);
  if (filters.entity) query.set('entity', filters.entity);
  if (filters.limit) query.set('limit', String(filters.limit));
  const queryString = query.toString();
  return queryString ? `?${queryString}` : '';
}

async function postPrivateJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function patchPrivateJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function downloadProtectedCsv(url: string, filename: string): Promise<void> {
  const response = await fetch(url, { headers: getAuthHeaders() });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

export function getDashboard(): Promise<DashboardData> {
  return getJson<DashboardData>('/api/v1/dashboard');
}

export function getOperationalReadiness(): Promise<OperationalReadiness> {
  return getJson<OperationalReadiness>('/health/readiness');
}

export function getCenters(): Promise<Center[]> {
  return getJson<Center[]>('/api/v1/centers');
}

export function updateCenterStatus(centerId: string, status: string, reason: string): Promise<Center> {
  return patchPrivateJson<Center>(`/api/v1/centers/${encodeURIComponent(centerId)}/status`, { status, reason });
}

export function getDashboardCsvUrl(): string {
  return `${API_BASE_URL}/api/v1/dashboard/export.csv`;
}

export function getExamAttemptsCsvUrl(): string {
  return `${API_BASE_URL}/api/v1/exams/export.csv`;
}

export function getAdminPaymentsCsvUrl(filters: PaymentFilters = {}): string {
  return `${API_BASE_URL}/api/v1/payments/admin/export.csv${buildPaymentQuery(filters)}`;
}

export function getAuditLogsCsvUrl(filters: AuditLogFilters = {}): string {
  return `${API_BASE_URL}/api/v1/supervision/audit-logs/export.csv${buildAuditQuery(filters)}`;
}

export function getAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogEntry[]> {
  return getPrivateJson<AuditLogEntry[]>(`/api/v1/supervision/audit-logs${buildAuditQuery({ ...filters, limit: filters.limit ?? 25 })}`);
}

export function getInstitutionalUsers(): Promise<InstitutionalUser[]> {
  return getPrivateJson<InstitutionalUser[]>('/api/v1/users?limit=50');
}

export function createInstitutionalUser(payload: InstitutionalUserCreatePayload): Promise<InstitutionalUser> {
  return postPrivateJson<InstitutionalUser>('/api/v1/users', payload);
}

export function updateInstitutionalUserRole(userId: string, role: string, reason: string): Promise<InstitutionalUser> {
  return patchPrivateJson<InstitutionalUser>(`/api/v1/users/${encodeURIComponent(userId)}/role`, { role, reason });
}

export function updateInstitutionalUserStatus(userId: string, isActive: boolean, reason: string): Promise<InstitutionalUser> {
  return patchPrivateJson<InstitutionalUser>(`/api/v1/users/${encodeURIComponent(userId)}/status`, { is_active: isActive, reason });
}

export function resetInstitutionalUserPassword(userId: string, newPassword: string, reason: string): Promise<InstitutionalUser> {
  return postPrivateJson<InstitutionalUser>(`/api/v1/users/${encodeURIComponent(userId)}/reset-password`, { new_password: newPassword, reason });
}

export function getAdminPaymentSummary(filters: PaymentFilters = {}): Promise<PaymentSummary> {
  return getPrivateJson<PaymentSummary>(`/api/v1/payments/admin/summary${buildPaymentQuery(filters)}`);
}

export function getInstitutionalReadiness(): Promise<InstitutionalReadiness> {
  return getPrivateJson<InstitutionalReadiness>('/api/v1/dashboard/institutional-readiness');
}

export function getInstitutionalReport(): Promise<InstitutionalReport> {
  return getPrivateJson<InstitutionalReport>('/api/v1/dashboard/institutional-report');
}

export function getInstitutionalActionCenter(): Promise<InstitutionalActionCenter> {
  return getPrivateJson<InstitutionalActionCenter>('/api/v1/dashboard/institutional-action-center');
}

export function getCandidateIdentityChecks(): Promise<CandidateIdentityCheck[]> {
  return getPrivateJson<CandidateIdentityCheck[]>('/api/v1/candidate-identity?limit=25');
}

export function decideCandidateIdentity(checkId: string, status: string, reason: string): Promise<CandidateIdentityCheck> {
  return postPrivateJson<CandidateIdentityCheck>(`/api/v1/candidate-identity/${encodeURIComponent(checkId)}/decision`, { status, reason });
}

export function getQuestionGovernanceItems(): Promise<QuestionGovernanceItem[]> {
  return getPrivateJson<QuestionGovernanceItem[]>('/api/v1/question-governance?limit=25');
}

export function decideQuestionGovernance(questionId: string, status: string, reason: string): Promise<QuestionGovernanceItem> {
  return postPrivateJson<QuestionGovernanceItem>(`/api/v1/question-governance/${encodeURIComponent(questionId)}/decision`, { status, reason });
}

export function getInstitutionalAuthorizations(): Promise<InstitutionalAuthorization[]> {
  return getPrivateJson<InstitutionalAuthorization[]>('/api/v1/institutional-authorizations?limit=25');
}

export function createInstitutionalAuthorization(payload: InstitutionalAuthorizationPayload): Promise<InstitutionalAuthorization> {
  return postPrivateJson<InstitutionalAuthorization>('/api/v1/institutional-authorizations', payload);
}

export function updateInstitutionalAuthorizationStatus(authorizationId: string, status: string, reason: string): Promise<InstitutionalAuthorization> {
  return patchPrivateJson<InstitutionalAuthorization>(`/api/v1/institutional-authorizations/${encodeURIComponent(authorizationId)}/status`, { status, reason });
}

export function getPaymentReconciliationItems(filters: PaymentFilters = {}): Promise<PaymentReconciliationItem[]> {
  const query = buildPaymentQuery({ ...filters, limit: filters.limit ?? 25 });
  return getPrivateJson<PaymentReconciliationItem[]>(`/api/v1/payments/admin/reconciliation/items${query}`);
}

export function getPaymentAlerts(filters: PaymentFilters = {}): Promise<PaymentAlert[]> {
  const query = buildPaymentQuery({ ...filters, limit: filters.limit ?? 25 });
  return getPrivateJson<PaymentAlert[]>(`/api/v1/payments/admin/reconciliation/alerts${query}`);
}

export function downloadDashboardCsv(): Promise<void> {
  return downloadProtectedCsv(getDashboardCsvUrl(), 'coderoute-dashboard-export.csv');
}

export function downloadInstitutionalReportCsv(): Promise<void> {
  return downloadProtectedCsv(`${API_BASE_URL}/api/v1/dashboard/institutional-report.csv`, 'coderoute-institutional-report.csv');
}

export function downloadExamAttemptsCsv(): Promise<void> {
  return downloadProtectedCsv(getExamAttemptsCsvUrl(), 'coderoute-exam-attempts.csv');
}

export function downloadAdminPaymentsCsv(filters: PaymentFilters = {}): Promise<void> {
  return downloadProtectedCsv(getAdminPaymentsCsvUrl(filters), 'coderoute-payments.csv');
}

export function downloadAuditLogsCsv(filters: AuditLogFilters = {}): Promise<void> {
  return downloadProtectedCsv(getAuditLogsCsvUrl(filters), 'coderoute-audit-logs.csv');
}

export function getEntrySummary(): Promise<EntrySummary> {
  return getJson<EntrySummary>('/api/v1/entries/summary');
}

export function getExamSummary(): Promise<ExamSummary> {
  return getJson<ExamSummary>('/api/v1/exams/summary');
}

export function validateEntry(payload: EntryValidationPayload): Promise<EntryValidationResult> {
  return postJson<EntryValidationResult>('/api/v1/entries/validate', payload);
}

export function createPayment(payload: PaymentPayload): Promise<PaymentResult> {
  return postJson<PaymentResult>('/api/v1/payments', payload);
}

export function getConvocationPdfUrl(reference: string): string {
  return `${API_BASE_URL}/api/v1/documents/convocations/${encodeURIComponent(reference)}.pdf`;
}

export function getExamCertificatePdfUrl(attemptId: string): string {
  return `${API_BASE_URL}/api/v1/exams/${encodeURIComponent(attemptId)}/certificate.pdf`;
}

export function verifyExamCertificate(attemptId: string): Promise<ExamCertificateVerification> {
  return getJson<ExamCertificateVerification>(`/api/v1/exams/${encodeURIComponent(attemptId)}/certificate/verify`);
}
