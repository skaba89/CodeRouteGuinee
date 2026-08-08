import { getAuthHeaders } from './authClient';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

export type EdgeFleetAlert = {
  code: string;
  severity: 'warning' | 'critical' | string;
  message: string;
};

export type EdgeFleetTelemetry = {
  active_leases: number;
  finalized_leases: number;
  synced_leases: number;
  sync_pending: number;
  revalidation_required: number;
  corrupt_leases: number;
  media_files: number;
  media_bytes: number;
};

export type EdgeFleetNode = {
  node_id: string;
  reference: string;
  center_id?: string | null;
  center_code?: string | null;
  label?: string | null;
  status: string;
  online: boolean;
  public_key_fingerprint?: string | null;
  capabilities: string[];
  last_sequence: number;
  last_seen_at?: string | null;
  software_version?: string | null;
  clock_skew_seconds?: number | null;
  telemetry?: EdgeFleetTelemetry | null;
  telemetry_at?: string | null;
  health_score: number;
  health_status: 'healthy' | 'degraded' | 'critical' | string;
  alerts: EdgeFleetAlert[];
  version_drift: boolean;
  missing_capabilities: string[];
  created_at?: string | null;
};

export type EdgeFleetCenter = {
  center_id: string;
  code: string;
  name: string;
  city: string;
  health_score: number;
  health_status: 'healthy' | 'degraded' | 'critical' | string;
  node_count: number;
  online_nodes: number;
  sync_pending: number;
  revalidation_required: number;
  corrupt_leases: number;
  version_drift_nodes: number;
  alerts: string[];
};

export type EdgeFleet = {
  generated_at: string;
  status: 'healthy' | 'degraded' | 'critical' | string;
  target_software_version: string;
  required_capabilities: string[];
  summary: {
    centers_total: number;
    centers_healthy: number;
    centers_degraded: number;
    centers_critical: number;
    centers_without_gateway: number;
    nodes_total: number;
    nodes_active: number;
    nodes_online: number;
    sync_pending: number;
    revalidation_required: number;
    corrupt_leases: number;
    version_drift_nodes: number;
    capability_drift_nodes: number;
  };
  rollout: {
    target_version: string;
    compliant_nodes: number;
    upgrade_required_nodes: number;
    blocked_nodes: number;
  };
  centers: EdgeFleetCenter[];
  nodes: EdgeFleetNode[];
};

async function fleetJson<T>(path: string): Promise<T> {
  const headers = new Headers(getAuthHeaders());
  headers.set('Accept', 'application/json');
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers,
  });
  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json() as { detail?: unknown };
      detail = typeof payload.detail === 'string' ? payload.detail : '';
    } catch { /* keep fallback */ }
    throw new Error(detail || `Supervision Edge indisponible (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getNationalEdgeFleet(): Promise<EdgeFleet> {
  return fleetJson<EdgeFleet>('/api/v1/center-edge/fleet');
}
