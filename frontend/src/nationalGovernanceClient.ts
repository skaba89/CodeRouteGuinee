import { getAuthHeaders } from './authClient';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

export type ExamPolicyParameters = {
  question_count: number;
  pass_threshold: number;
  duration_minutes: number;
  category_distribution: Record<string, number>;
  one_attempt_per_session: boolean;
  retake_cooldown_hours?: number;
};

export type LegalReference = {
  reference: string;
  title: string;
  issued_on?: string | null;
  source_ref?: string | null;
};

export type PolicyDocument = {
  kind: string;
  schema_version: number;
  code: string;
  version: string;
  parameters: ExamPolicyParameters;
  legal_references: LegalReference[];
  rationale: string;
  approvals: Array<{ actor_id: string; role: string; approved_at: string; note: string }>;
  document_sha256: string;
  activated_at?: string | null;
  supersedes_reference?: string | null;
};

export type GovernanceRecord<T = Record<string, unknown>> = {
  id: string;
  reference: string;
  authority: string;
  title: string;
  status: string;
  valid_from?: string | null;
  valid_until?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  document: T;
};

export type GovernanceCheck = {
  code: string;
  required: boolean;
  status: 'pass' | 'fail';
  evidence: unknown;
};

export type GovernanceReadiness = {
  generated_at: string;
  go_live_allowed: boolean;
  active_policy: GovernanceRecord<PolicyDocument> | null;
  checks: GovernanceCheck[];
  blockers: string[];
};

export type TechnicalContract = {
  runtime: ExamPolicyParameters;
  active_policy: GovernanceRecord<PolicyDocument> | null;
  alignment: { aligned: boolean; runtime?: ExamPolicyParameters; drift: Array<Record<string, unknown>> };
};

export type HomologationEvidenceCode =
  | 'dntt_exam_rules'
  | 'legal_review'
  | 'security_assessment'
  | 'operations_readiness'
  | 'content_signoff';

export type HomologationEvidence = {
  reference: string;
  artifact_sha256: string;
  issued_at: string;
  note?: string | null;
  attached_by?: string;
  attached_at?: string;
};

export type HomologationDocument = {
  kind: string;
  policy_reference: string;
  policy_sha256: string;
  target_scope: 'pilot' | 'national';
  evidence: Partial<Record<HomologationEvidenceCode, HomologationEvidence>>;
  evidence_history?: Array<{
    code: HomologationEvidenceCode;
    reference?: string | null;
    artifact_sha256?: string | null;
    issued_at?: string | null;
    replaced_by?: string;
    replaced_at?: string;
  }>;
  approvals: Array<{ actor_id: string; role: string; approved_at: string; note: string }>;
  decision?: Record<string, unknown> | null;
  document_sha256: string;
};

async function csrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/csrf-token`, { credentials: 'include' });
  if (!response.ok) throw new Error(`CSRF indisponible (${response.status})`);
  return (await response.json() as { csrf_token: string }).csrf_token;
}

async function request<T>(path: string, init?: RequestInit, mutating = false): Promise<T> {
  const headers = new Headers(getAuthHeaders());
  headers.set('Accept', 'application/json');
  if (init?.body) headers.set('Content-Type', 'application/json');
  if (mutating) headers.set('X-CSRF-Token', await csrfToken());
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, credentials: 'include', headers });
  if (!response.ok) {
    let detail = `Gouvernance nationale indisponible (${response.status})`;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === 'string') detail = payload.detail;
      else if (payload.detail && typeof payload.detail === 'object') {
        const object = payload.detail as { code?: unknown; blockers?: unknown; missing?: unknown; invalid?: unknown };
        if (object.code) detail = String(object.code);
        if (Array.isArray(object.blockers) && object.blockers.length) detail += ` — ${object.blockers.join(', ')}`;
        if (Array.isArray(object.missing) && object.missing.length) detail += ` — manquantes: ${object.missing.join(', ')}`;
        if (Array.isArray(object.invalid) && object.invalid.length) detail += ' — intégrité de preuve invalide';
      }
    } catch { /* fallback */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function getGovernanceReadiness(): Promise<GovernanceReadiness> {
  return request('/api/v1/national-governance/readiness');
}

export function getTechnicalContract(): Promise<TechnicalContract> {
  return request('/api/v1/national-governance/technical-contract');
}

export function getNationalPolicies(): Promise<Array<GovernanceRecord<PolicyDocument>>> {
  return request('/api/v1/national-governance/policies');
}

export function getHomologationDossiers(): Promise<Array<GovernanceRecord<HomologationDocument>>> {
  return request('/api/v1/national-governance/homologation-dossiers');
}

export function createNationalPolicy(payload: {
  code: string;
  version: string;
  title: string;
  authority: string;
  parameters: ExamPolicyParameters;
  legal_references: LegalReference[];
  rationale: string;
}): Promise<GovernanceRecord<PolicyDocument>> {
  return request('/api/v1/national-governance/policies', { method: 'POST', body: JSON.stringify(payload) }, true);
}

export function submitNationalPolicy(reference: string): Promise<GovernanceRecord<PolicyDocument>> {
  return request(`/api/v1/national-governance/policies/${encodeURIComponent(reference)}/submit`, { method: 'POST' }, true);
}

export function approveNationalPolicy(reference: string, note: string): Promise<GovernanceRecord<PolicyDocument>> {
  return request(`/api/v1/national-governance/policies/${encodeURIComponent(reference)}/approve`, {
    method: 'POST', body: JSON.stringify({ note }),
  }, true);
}

export function activateNationalPolicy(reference: string): Promise<GovernanceRecord<PolicyDocument>> {
  return request(`/api/v1/national-governance/policies/${encodeURIComponent(reference)}/activate`, { method: 'POST' }, true);
}

export function createHomologationDossier(payload: {
  title: string;
  policy_reference: string;
  target_scope: 'pilot' | 'national';
}): Promise<GovernanceRecord<HomologationDocument>> {
  return request('/api/v1/national-governance/homologation-dossiers', {
    method: 'POST', body: JSON.stringify(payload),
  }, true);
}

export function attachHomologationEvidence(
  reference: string,
  payload: {
    code: HomologationEvidenceCode;
    reference: string;
    artifact_sha256: string;
    issued_at: string;
    note?: string | null;
  },
): Promise<GovernanceRecord<HomologationDocument>> {
  return request(`/api/v1/national-governance/homologation-dossiers/${encodeURIComponent(reference)}/evidence`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true);
}

export function submitHomologationDossier(reference: string): Promise<GovernanceRecord<HomologationDocument>> {
  return request(`/api/v1/national-governance/homologation-dossiers/${encodeURIComponent(reference)}/submit`, { method: 'POST' }, true);
}

export function approveHomologationDossier(reference: string, note: string): Promise<GovernanceRecord<HomologationDocument>> {
  return request(`/api/v1/national-governance/homologation-dossiers/${encodeURIComponent(reference)}/approve`, {
    method: 'POST', body: JSON.stringify({ note }),
  }, true);
}

export function decideHomologationDossier(
  reference: string,
  approve: boolean,
  note: string,
): Promise<GovernanceRecord<HomologationDocument>> {
  return request(`/api/v1/national-governance/homologation-dossiers/${encodeURIComponent(reference)}/decision?approve=${approve ? 'true' : 'false'}`, {
    method: 'POST', body: JSON.stringify({ note }),
  }, true);
}
