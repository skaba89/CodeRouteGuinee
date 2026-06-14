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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
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

export function getDashboard(): Promise<DashboardData> {
  return getJson<DashboardData>('/api/v1/dashboard');
}

export function getDashboardCsvUrl(): string {
  return `${API_BASE_URL}/api/v1/dashboard/export.csv`;
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