import { getAuthHeaders } from './authClient';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

export type ReliabilityStatus = {
  generated_at: string;
  policy: {
    slo?: {
      availability_percent?: number;
      p95_latency_ms?: number;
      max_5xx_percent?: number;
    };
    dr?: {
      rpo_minutes?: number;
      rto_minutes?: number;
      backup_required?: boolean;
      off_region_required?: boolean;
      primary_region?: string | null;
      target_region?: string | null;
      bucket_configured?: boolean;
      encryption_key_id?: string | null;
    };
    observability?: {
      metrics_enabled?: boolean;
      reliability_evidence_enabled?: boolean;
    };
  };
  last_evidence: {
    backup_uploaded?: string | null;
    restore_drill_passed?: string | null;
    pitr_drill_passed?: string | null;
    ha_failover_probe_passed?: string | null;
  };
};

export async function getReliabilityStatus(): Promise<ReliabilityStatus> {
  const headers = new Headers(getAuthHeaders());
  headers.set('Accept', 'application/json');
  const response = await fetch(`${API_BASE_URL}/api/v1/operations/reliability`, {
    credentials: 'include',
    headers,
  });
  if (!response.ok) {
    let detail = `PRA/fiabilité indisponible (${response.status})`;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === 'string') detail = payload.detail;
    } catch { /* fallback */ }
    throw new Error(detail);
  }
  return response.json() as Promise<ReliabilityStatus>;
}
