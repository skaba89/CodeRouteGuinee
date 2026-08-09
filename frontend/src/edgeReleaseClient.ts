import { getAuthHeaders } from './authClient';

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
);

export type EdgeSupplyChainEvidence = {
  builder: string;
  source_commit_sha: string;
  workflow_ref: string;
  provenance_url: string;
  sbom_sha256: string;
  sbom_attestation_url?: string | null;
  subject_sha256: string;
  vulnerability_scan_status: 'passed' | 'failed';
};

export type EdgeReleaseManifest = {
  kind: string;
  version: number;
  release_id: string;
  software_version: string;
  artifact: {
    format: string;
    url: string;
    sha256: string;
    size_bytes: number;
  };
  created_at: string;
  min_current_version?: string | null;
  release_notes?: string | null;
  supply_chain?: EdgeSupplyChainEvidence | null;
};

export type EdgeRelease = {
  release_id: string;
  reference: string;
  status: string;
  rollout_status: string;
  rollout_percent: number;
  canary_node_ids: string[];
  allowed_center_ids: string[];
  rollback_release_id?: string | null;
  manifest: EdgeReleaseManifest;
  manifest_hash: string;
  manifest_signature_b64: string;
  signing_key_id: string;
  created_at?: string | null;
  updated_at?: string | null;
  supply_chain_ready?: boolean;
};

export type EdgeReleaseCreatePayload = {
  software_version: string;
  artifact_url: string;
  artifact_sha256: string;
  artifact_size_bytes: number;
  min_current_version?: string;
  release_notes?: string;
  canary_node_ids?: string[];
  allowed_center_ids?: string[];
  rollback_release_id?: string;
};

export type EdgeRolloutPayload = {
  rollout_status: string;
  rollout_percent: number;
  canary_node_ids?: string[];
  allowed_center_ids?: string[];
  rollback_release_id?: string;
  reason: string;
};

export type EdgeReleaseAttestation = {
  attestation_id: string;
  node_id?: string | null;
  center_id?: string | null;
  result: string;
  software_version?: string | null;
  attested_at?: string | null;
};

export type EdgeReleaseRollout = {
  release: EdgeRelease;
  eligible_nodes: number;
  attestation_counts: {
    staged: number;
    installed: number;
    failed: number;
    rolled_back: number;
  };
  attestations: EdgeReleaseAttestation[];
};

async function csrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/csrf-token`, { credentials: 'include' });
  if (!response.ok) throw new Error(`CSRF indisponible (${response.status})`);
  const payload = await response.json() as { csrf_token: string };
  return payload.csrf_token;
}

async function request<T>(path: string, init?: RequestInit, mutating = false): Promise<T> {
  const headers = new Headers(getAuthHeaders());
  headers.set('Accept', 'application/json');
  if (init?.body) headers.set('Content-Type', 'application/json');
  if (mutating) headers.set('X-CSRF-Token', await csrfToken());
  if (init?.headers) new Headers(init.headers).forEach((value, key) => headers.set(key, value));

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  });
  if (!response.ok) {
    let detail = `API release Edge ${response.status}`;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === 'string') detail = payload.detail;
      else if (payload.detail && typeof payload.detail === 'object' && 'message' in payload.detail) {
        detail = String((payload.detail as { message?: unknown }).message || detail);
      }
    } catch { /* fallback */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function getEdgeReleases(): Promise<EdgeRelease[]> {
  return request<EdgeRelease[]>('/api/v1/center-edge/releases');
}

export function createEdgeRelease(payload: EdgeReleaseCreatePayload): Promise<EdgeRelease> {
  return request<EdgeRelease>('/api/v1/center-edge/releases', {
    method: 'POST', body: JSON.stringify(payload),
  }, true);
}

export function attachEdgeSupplyChainEvidence(
  releaseId: string,
  evidence: EdgeSupplyChainEvidence,
): Promise<EdgeRelease> {
  return request<EdgeRelease>(`/api/v1/center-edge/releases/${encodeURIComponent(releaseId)}/supply-chain`, {
    method: 'POST', body: JSON.stringify(evidence),
  }, true);
}

export function updateEdgeReleaseRollout(releaseId: string, payload: EdgeRolloutPayload): Promise<EdgeRelease> {
  return request<EdgeRelease>(`/api/v1/center-edge/releases/${encodeURIComponent(releaseId)}/rollout`, {
    method: 'POST', body: JSON.stringify(payload),
  }, true);
}

export function getEdgeReleaseRollout(releaseId: string): Promise<EdgeReleaseRollout> {
  return request<EdgeReleaseRollout>(`/api/v1/center-edge/releases/${encodeURIComponent(releaseId)}/rollout`);
}
