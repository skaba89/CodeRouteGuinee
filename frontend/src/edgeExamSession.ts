import { getOrCreateExamDeviceKey } from './deviceIdentity';

const PENDING_BOOTSTRAP_KEY = 'coderoute:edge:pending-bootstrap:v1';
const EDGE_SESSION_PREFIX = 'coderoute:edge:session:v1:';
const ACTIVE_ATTEMPT_KEY = 'coderoute:official-exam:active-attempt';

type EdgeBootstrap = {
  edge_url: string;
  attempt_id: string;
  claim_token: string;
  claim_expires_at?: number;
};

export type EdgeSession = {
  edge_url: string;
  attempt_id: string;
  access_token: string;
  last_answers: Record<string, string>;
};

export type EdgeExamState = {
  attempt_id: string;
  lease_id: string;
  status: 'active' | 'finalized' | 'synced' | string;
  elapsed_ms: number;
  duration_ms: number;
  remaining_ms: number;
  answers: Record<string, string>;
  questions: Array<{
    id: string;
    number: number;
    category: string;
    text: string;
    options: string[];
    media_type?: string | null;
    media_url?: string | null;
    media_alt?: string | null;
    audio_url?: string | null;
  }>;
  language?: string;
  station?: Record<string, unknown> | null;
};

function decodeBase64UrlJson(value: string): unknown {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
  const raw = atob(padded);
  const bytes = Uint8Array.from(raw, char => char.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes));
}

function isSecureEdgeUrl(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:';
  } catch {
    return false;
  }
}

function normalizeBootstrap(value: unknown): EdgeBootstrap | null {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Record<string, unknown>;
  if (!isSecureEdgeUrl(raw.edge_url)) return null;
  if (typeof raw.attempt_id !== 'string' || raw.attempt_id.length < 8) return null;
  if (typeof raw.claim_token !== 'string' || raw.claim_token.length < 32) return null;
  return {
    edge_url: raw.edge_url.replace(/\/$/, ''),
    attempt_id: raw.attempt_id,
    claim_token: raw.claim_token,
    claim_expires_at: typeof raw.claim_expires_at === 'number' ? raw.claim_expires_at : undefined,
  };
}

export function captureEdgeBootstrapFromHash(): void {
  if (typeof window === 'undefined') return;
  const hash = window.location.hash || '';
  if (!hash.startsWith('#/exam?')) return;
  const encoded = new URLSearchParams(hash.slice(hash.indexOf('?') + 1)).get('edge');
  if (!encoded) return;
  try {
    const bootstrap = normalizeBootstrap(decodeBase64UrlJson(encoded));
    if (!bootstrap) throw new Error('Bootstrap Edge invalide');
    window.sessionStorage.setItem(PENDING_BOOTSTRAP_KEY, JSON.stringify(bootstrap));
  } catch {
    window.sessionStorage.removeItem(PENDING_BOOTSTRAP_KEY);
  } finally {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#/exam`);
  }
}

export function hasPendingEdgeBootstrap(): boolean {
  try { return Boolean(window.sessionStorage.getItem(PENDING_BOOTSTRAP_KEY)); } catch { return false; }
}

function readPendingBootstrap(): EdgeBootstrap | null {
  try {
    const raw = window.sessionStorage.getItem(PENDING_BOOTSTRAP_KEY);
    return raw ? normalizeBootstrap(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function sessionKey(attemptId: string): string {
  return `${EDGE_SESSION_PREFIX}${attemptId}`;
}

function saveSession(session: EdgeSession): void {
  window.sessionStorage.setItem(sessionKey(session.attempt_id), JSON.stringify(session));
}

export function getEdgeSession(attemptId: string | null | undefined): EdgeSession | null {
  if (!attemptId) return null;
  try {
    const raw = window.sessionStorage.getItem(sessionKey(attemptId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<EdgeSession>;
    if (!isSecureEdgeUrl(parsed.edge_url) || parsed.attempt_id !== attemptId || typeof parsed.access_token !== 'string') return null;
    return {
      edge_url: parsed.edge_url.replace(/\/$/, ''),
      attempt_id: attemptId,
      access_token: parsed.access_token,
      last_answers: parsed.last_answers && typeof parsed.last_answers === 'object'
        ? parsed.last_answers as Record<string, string>
        : {},
    };
  } catch {
    return null;
  }
}

export function clearEdgeSession(attemptId: string): void {
  try { window.sessionStorage.removeItem(sessionKey(attemptId)); } catch { /* no-op */ }
}

export async function claimPendingEdgeSession(): Promise<EdgeSession | null> {
  const pending = readPendingBootstrap();
  if (!pending) return null;
  if (pending.claim_expires_at && pending.claim_expires_at * 1000 < Date.now()) {
    window.sessionStorage.removeItem(PENDING_BOOTSTRAP_KEY);
    throw new Error('Le lien Edge a expiré. Demandez une nouvelle activation au centre.');
  }

  const stationKey = getOrCreateExamDeviceKey();
  const response = await fetch(`${pending.edge_url}/v1/claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      attempt_id: pending.attempt_id,
      claim_token: pending.claim_token,
      station_device_key: stationKey,
    }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Activation Edge refusée (${response.status})${detail ? ` — ${detail.slice(0, 240)}` : ''}`);
  }
  const payload = await response.json() as Record<string, unknown>;
  if (payload.attempt_id !== pending.attempt_id || typeof payload.access_token !== 'string') {
    throw new Error('Réponse de claim Edge invalide');
  }

  const session: EdgeSession = {
    edge_url: pending.edge_url,
    attempt_id: pending.attempt_id,
    access_token: payload.access_token,
    last_answers: {},
  };
  saveSession(session);
  window.sessionStorage.setItem(ACTIVE_ATTEMPT_KEY, pending.attempt_id);
  window.sessionStorage.removeItem(PENDING_BOOTSTRAP_KEY);
  return session;
}

function edgeHeaders(session: EdgeSession): Record<string, string> {
  return {
    'X-Edge-Access-Token': session.access_token,
    'X-CodeRoute-Station-Key': getOrCreateExamDeviceKey(),
  };
}

async function edgeJson<T>(session: EdgeSession, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  Object.entries(edgeHeaders(session)).forEach(([key, value]) => headers.set(key, value));
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${session.edge_url}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Gateway Edge indisponible (${response.status})${detail ? ` — ${detail.slice(0, 240)}` : ''}`);
  }
  return response.json() as Promise<T>;
}

export async function getEdgeExamState(attemptId: string): Promise<EdgeExamState> {
  const session = getEdgeSession(attemptId);
  if (!session) throw new Error('Session Edge introuvable');
  const state = await edgeJson<EdgeExamState>(session, `/v1/exams/${encodeURIComponent(attemptId)}`);
  session.last_answers = { ...(state.answers || {}) };
  saveSession(session);
  return state;
}

export async function getEdgeExamQuestions(attemptId: string) {
  const state = await getEdgeExamState(attemptId);
  return {
    attempt_id: attemptId,
    questions: state.questions,
    duration_seconds: Math.max(1, Math.round(state.duration_ms / 1000)),
    threshold: 35,
  };
}

export async function saveEdgeAnswerSnapshot(attemptId: string, answers: Record<string, string>) {
  const session = getEdgeSession(attemptId);
  if (!session) throw new Error('Session Edge introuvable');
  const previous = session.last_answers || {};
  for (const [questionId, answer] of Object.entries(answers)) {
    if (previous[questionId] === answer) continue;
    await edgeJson(session, `/v1/exams/${encodeURIComponent(attemptId)}/answers`, {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer }),
    });
    previous[questionId] = answer;
  }
  session.last_answers = { ...previous };
  saveSession(session);
  return { answers: { ...previous } };
}

export async function finalizeEdgeExam(attemptId: string): Promise<{ queued_for_sync: boolean }> {
  const session = getEdgeSession(attemptId);
  if (!session) throw new Error('Session Edge introuvable');
  return edgeJson(session, `/v1/exams/${encodeURIComponent(attemptId)}/finalize`, { method: 'POST' });
}

export function isEdgeAttempt(attemptId: string | null | undefined): boolean {
  return Boolean(getEdgeSession(attemptId));
}
