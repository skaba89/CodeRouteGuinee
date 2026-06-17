import { getAuthHeaders } from './authClient';

export type DashboardData = {
  candidates: number;
  accredited_centers: number;
  exam_sessions: number;
  questions: number;
  fraud_alerts: number;
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

export function getDashboardCsvUrl(): string {
  return `${API_BASE_URL}/api/v1/dashboard/export.csv`;
}

export function getExamAttemptsCsvUrl(): string {
  return `${API_BASE_URL}/api/v1/exams/export.csv`;
}

export function getAdminPaymentsCsvUrl(filters: PaymentFilters = {}): string {
  return `${API_BASE_URL}/api/v1/payments/admin/export.csv${buildPaymentQuery(filters)}`;
}

export function getAuditLogs(): Promise<AuditLogEntry[]> {
  return getPrivateJson<AuditLogEntry[]>('/api/v1/supervision/audit-logs?limit=25');
}

export function getAdminPaymentSummary(filters: PaymentFilters = {}): Promise<PaymentSummary> {
  return getPrivateJson<PaymentSummary>(`/api/v1/payments/admin/summary${buildPaymentQuery(filters)}`);
}

export function getInstitutionalReadiness(): Promise<InstitutionalReadiness> {
  return getPrivateJson<InstitutionalReadiness>('/api/v1/dashboard/institutional-readiness');
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

export function downloadExamAttemptsCsv(): Promise<void> {
  return downloadProtectedCsv(getExamAttemptsCsvUrl(), 'coderoute-exam-attempts.csv');
}

export function downloadAdminPaymentsCsv(filters: PaymentFilters = {}): Promise<void> {
  return downloadProtectedCsv(getAdminPaymentsCsvUrl(filters), 'coderoute-payments.csv');
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
