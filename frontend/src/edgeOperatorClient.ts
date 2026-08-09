export type EdgeLeaseSummary = {
  attempt_id: string;
  lease_id: string;
  status: string;
  runtime_state: string;
  deadline_at?: string | null;
  duration_ms: number;
  elapsed_ms?: number | null;
  question_count: number;
  event_count: number;
  claim_state: string;
  claim_expires_at?: number | null;
  sync_pending: boolean;
  station: {
    center_station_id?: string | null;
    device_key?: string | null;
    label?: string | null;
    room?: string | null;
  };
  created_at: number;
  updated_at: number;
};

export type EdgeLocalReleaseState = {
  enabled: boolean;
  staged?: {
    release_id?: string;
    action?: string;
    software_version?: string;
    artifact_sha256?: string;
    artifact_size_bytes?: number;
    verified?: boolean;
    corrupt?: boolean;
  } | null;
  install_receipt?: {
    release_id?: string;
    software_version?: string;
    artifact_sha256?: string;
    result?: string;
    corrupt?: boolean;
  } | null;
};

export type EdgeReleaseOffer = {
  update_available: boolean;
  action: 'none' | 'install' | 'rollback' | string;
  current_version?: string;
  source_release_id?: string;
  rollout_status?: string;
  release?: {
    release_id: string;
    manifest: {
      software_version: string;
      artifact: { sha256: string; size_bytes: number; url: string; format: string };
      release_notes?: string | null;
    };
  };
};

export type EdgeReleaseStageResult = {
  staged: boolean;
  reason?: string;
  release_id?: string;
  action?: string;
  software_version?: string;
  artifact_sha256?: string;
  artifact_size_bytes?: number;
  verified?: boolean;
};

export type EdgeOperatorStatus = {
  node_id: string;
  center_id: string;
  software_version: string;
  lease_counts: Record<string, number>;
  leases: EdgeLeaseSummary[];
  sync_pending: number;
  revalidation_required: number;
  media_cache: { files: number; bytes: number };
  release?: EdgeLocalReleaseState;
};

export type EdgeHealth = {
  status: string;
  node_id: string;
  center_id: string;
  software_version: string;
  lease_counts: Record<string, number>;
};

export type EdgeActivation = {
  attempt_id: string;
  lease_id: string;
  claim_expires_at: number;
  deadline_at: string;
  duration_seconds: number;
  question_count: number;
  candidate_url: string;
  station?: Record<string, unknown>;
};

const EDGE_URL_KEY = 'coderoute:center-edge:url:v1';
const EDGE_OPERATOR_TOKEN_KEY = 'coderoute:center-edge:operator-token:v1';

function normalizedUrl(value: string): string {
  const raw = value.trim().replace(/\/$/, '');
  const url = new URL(raw);
  const localLab = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  if (url.protocol !== 'https:' && !(localLab && url.protocol === 'http:')) {
    throw new Error('Le gateway Edge doit utiliser HTTPS (HTTP autorisé uniquement sur localhost).');
  }
  if (url.username || url.password) throw new Error('Ne placez jamais de secret dans l’URL du gateway.');
  return url.origin;
}

export function getSavedEdgeUrl(): string {
  try { return window.localStorage.getItem(EDGE_URL_KEY) ?? ''; } catch { return ''; }
}

export function getSessionOperatorToken(): string {
  try { return window.sessionStorage.getItem(EDGE_OPERATOR_TOKEN_KEY) ?? ''; } catch { return ''; }
}

export function saveEdgeOperatorConnection(url: string, token: string): { url: string; token: string } {
  const safeUrl = normalizedUrl(url);
  const safeToken = token.trim();
  if (safeToken.length < 32) throw new Error('Le secret opérateur Edge doit contenir au moins 32 caractères.');
  try {
    window.localStorage.setItem(EDGE_URL_KEY, safeUrl);
    window.sessionStorage.setItem(EDGE_OPERATOR_TOKEN_KEY, safeToken);
  } catch {
    // Les valeurs restent utilisables pour la requête courante même si le stockage est verrouillé.
  }
  return { url: safeUrl, token: safeToken };
}

export function clearEdgeOperatorToken(): void {
  try { window.sessionStorage.removeItem(EDGE_OPERATOR_TOKEN_KEY); } catch { /* no-op */ }
}

async function parseError(response: Response): Promise<Error> {
  let detail = `Gateway Edge — erreur ${response.status}`;
  try {
    const body = await response.json() as { detail?: unknown };
    if (typeof body.detail === 'string') detail = body.detail;
    else if (body.detail && typeof body.detail === 'object' && 'message' in body.detail) {
      detail = String((body.detail as { message: unknown }).message);
    }
  } catch { /* keep HTTP fallback */ }
  return new Error(detail);
}

async function edgeFetch<T>(url: string, path: string, token?: string, init?: RequestInit): Promise<T> {
  const safeUrl = normalizedUrl(url);
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers['X-Edge-Operator-Token'] = token;
  const response = await fetch(`${safeUrl}${path}`, {
    ...init,
    headers,
    cache: 'no-store',
  });
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

export function getEdgeHealth(url: string): Promise<EdgeHealth> {
  return edgeFetch<EdgeHealth>(url, '/health');
}

export function getEdgeOperatorStatus(url: string, token: string): Promise<EdgeOperatorStatus> {
  return edgeFetch<EdgeOperatorStatus>(url, '/operator/status', token);
}

export function sendEdgeHeartbeat(url: string, token: string): Promise<Record<string, unknown>> {
  return edgeFetch<Record<string, unknown>>(url, '/operator/heartbeat', token, { method: 'POST' });
}

export async function activateEdgeLease(
  url: string,
  token: string,
  attemptId: string,
  stationDeviceKey: string,
  lang = 'fr',
): Promise<EdgeActivation> {
  const result = await edgeFetch<EdgeActivation & { claim_token?: unknown }>(url, '/operator/leases', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      attempt_id: attemptId.trim(),
      station_device_key: stationDeviceKey.trim(),
      lang,
    }),
  });
  return {
    attempt_id: result.attempt_id,
    lease_id: result.lease_id,
    claim_expires_at: result.claim_expires_at,
    deadline_at: result.deadline_at,
    duration_seconds: result.duration_seconds,
    question_count: result.question_count,
    candidate_url: result.candidate_url,
    station: result.station,
  };
}

export function syncEdgeAttempt(url: string, token: string, attemptId: string): Promise<Record<string, unknown>> {
  return edgeFetch<Record<string, unknown>>(url, `/operator/sync/${encodeURIComponent(attemptId)}`, token, { method: 'POST' });
}

export function checkLocalEdgeRelease(url: string, token: string): Promise<EdgeReleaseOffer> {
  return edgeFetch<EdgeReleaseOffer>(url, '/operator/releases/check', token, { method: 'POST' });
}

export function stageLocalEdgeRelease(url: string, token: string): Promise<EdgeReleaseStageResult> {
  return edgeFetch<EdgeReleaseStageResult>(url, '/operator/releases/stage', token, { method: 'POST' });
}

export function getLocalEdgeReleaseStatus(url: string, token: string): Promise<EdgeLocalReleaseState> {
  return edgeFetch<EdgeLocalReleaseState>(url, '/operator/releases/status', token);
}

export function attestLocalEdgeInstall(url: string, token: string): Promise<Record<string, unknown>> {
  return edgeFetch<Record<string, unknown>>(url, '/operator/releases/attest-install', token, { method: 'POST' });
}
