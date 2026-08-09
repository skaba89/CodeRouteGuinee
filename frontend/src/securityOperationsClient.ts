import { getAuthHeaders } from './authClient';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

export type SecurityAlert = {
  code: string;
  severity: 'warning' | 'critical' | string;
};

export type SecurityGoLiveControl = {
  code: string;
  passed: boolean;
  detail: string;
};

export type SecurityOperationsStatus = {
  status: 'disabled' | 'ok' | 'warning' | 'critical' | string;
  generated_at: string;
  soc_policy: {
    enabled: boolean;
    audit_chain_enabled: boolean;
    audit_verify_interval_seconds: number;
    otel: {
      traces_enabled: boolean;
      endpoint_configured: boolean;
      service_name: string;
      sample_ratio: number;
    };
    waf: { required: boolean; provider?: string | null };
    siem: { required: boolean };
  };
  audit_chain: {
    enabled?: boolean;
    valid?: boolean;
    reason?: string | null;
    total_entries?: number;
    legacy_entries?: number;
    anchor_seq?: number;
    head_seq?: number;
    head_hash?: string | null;
  };
  go_live?: {
    ready: boolean;
    controls: SecurityGoLiveControl[];
    blockers: string[];
    external_evidence_still_required: string[];
  };
  signals: {
    login_failed_15m: number;
    login_blocked_15m: number;
    login_failed_24h: number;
    suspicious_devices: number;
    critical_center_incidents: number;
  };
  alerts: SecurityAlert[];
};

export async function getSecurityOperationsStatus(): Promise<SecurityOperationsStatus> {
  const headers = new Headers(getAuthHeaders());
  headers.set('Accept', 'application/json');
  const response = await fetch(`${API_BASE_URL}/api/v1/operations/security/status`, {
    credentials: 'include',
    headers,
  });
  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json() as { detail?: unknown };
      detail = typeof payload.detail === 'string' ? payload.detail : '';
    } catch { /* fallback */ }
    throw new Error(detail || `Supervision sécurité indisponible (${response.status})`);
  }
  return response.json() as Promise<SecurityOperationsStatus>;
}
