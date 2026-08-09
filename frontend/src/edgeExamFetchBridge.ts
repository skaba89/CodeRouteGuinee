import {
  finalizeEdgeExam,
  getEdgeExamQuestions,
  getEdgeExamState,
  isEdgeAttempt,
  saveEdgeAnswerSnapshot,
} from './edgeExamSession';

const PATCH_MARKER = '__coderouteEdgeExamFetchBridgeV1';
const PENDING_RESULT_KEY = 'coderoute:edge:pending-result:v1';

type JsonRecord = Record<string, unknown>;

type MatchedExamRequest = {
  attemptId: string;
  action: 'questions' | 'status' | 'answers' | 'submit' | 'timeout-submit';
};

function requestUrl(input: RequestInfo | URL): URL | null {
  try {
    const raw = typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;
    return new URL(raw, window.location.origin);
  } catch {
    return null;
  }
}

function resolveMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return init.method.toUpperCase();
  if (typeof Request !== 'undefined' && input instanceof Request) return input.method.toUpperCase();
  return 'GET';
}

function matchExamRequest(input: RequestInfo | URL): MatchedExamRequest | null {
  const url = requestUrl(input);
  if (!url) return null;
  const match = url.pathname.match(
    /^\/api\/v1\/exams\/([^/]+)\/(questions|status|answers|submit|timeout-submit)$/,
  );
  if (!match) return null;
  try {
    return {
      attemptId: decodeURIComponent(match[1]),
      action: match[2] as MatchedExamRequest['action'],
    };
  } catch {
    return null;
  }
}

async function readJsonBody(input: RequestInfo | URL, init?: RequestInit): Promise<JsonRecord> {
  if (typeof init?.body === 'string') {
    try { return JSON.parse(init.body) as JsonRecord; } catch { return {}; }
  }
  if (typeof Request !== 'undefined' && input instanceof Request) {
    try {
      const text = await input.clone().text();
      return text ? JSON.parse(text) as JsonRecord : {};
    } catch {
      return {};
    }
  }
  return {};
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    },
  });
}

function markPendingEdgeResult(attemptId: string): void {
  try { window.sessionStorage.setItem(PENDING_RESULT_KEY, attemptId); } catch { /* no-op */ }
}

function routeToPendingResult(): void {
  if (window.location.hash !== '#/edge-pending') {
    window.location.hash = '#/edge-pending';
  }
}

export function getPendingEdgeResultAttempt(): string | null {
  try { return window.sessionStorage.getItem(PENDING_RESULT_KEY); } catch { return null; }
}

export function clearPendingEdgeResult(): void {
  try { window.sessionStorage.removeItem(PENDING_RESULT_KEY); } catch { /* no-op */ }
}

async function edgeStatusResponse(attemptId: string): Promise<Response> {
  const state = await getEdgeExamState(attemptId);
  const localFinalized = state.status === 'finalized' || state.status === 'synced';

  if (localFinalized) {
    markPendingEdgeResult(attemptId);
    queueMicrotask(routeToPendingResult);
  }

  return jsonResponse({
    attempt_id: attemptId,
    status: localFinalized ? 'submitted' : 'started',
    remaining_seconds: Math.max(0, Math.ceil((state.remaining_ms || 0) / 1000)),
    elapsed_seconds: Math.max(0, Math.floor((state.elapsed_ms || 0) / 1000)),
    total_seconds: Math.max(1, Math.ceil((state.duration_ms || 0) / 1000)),
    question_count: Array.isArray(state.questions) ? state.questions.length : 0,
    score: null,
    passed: null,
    expired: (state.remaining_ms || 0) <= 0,
  });
}

async function handleEdgeRequest(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  matched: MatchedExamRequest,
): Promise<Response | null> {
  const { attemptId, action } = matched;
  if (!isEdgeAttempt(attemptId)) return null;

  const method = resolveMethod(input, init);

  if (action === 'questions' && method === 'GET') {
    return jsonResponse(await getEdgeExamQuestions(attemptId));
  }

  if (action === 'status' && method === 'GET') {
    return edgeStatusResponse(attemptId);
  }

  if (action === 'answers' && method === 'GET') {
    const state = await getEdgeExamState(attemptId);
    return jsonResponse({ answers: state.answers || {} });
  }

  if (action === 'answers' && method === 'POST') {
    const body = await readJsonBody(input, init);
    const answers = body.answers && typeof body.answers === 'object'
      ? body.answers as Record<string, string>
      : {};
    const saved = await saveEdgeAnswerSnapshot(attemptId, answers);
    return jsonResponse(saved);
  }

  if ((action === 'submit' || action === 'timeout-submit') && method === 'POST') {
    if (action === 'submit') {
      const body = await readJsonBody(input, init);
      const answers = body.answers && typeof body.answers === 'object'
        ? body.answers as Record<string, string>
        : {};
      await saveEdgeAnswerSnapshot(attemptId, answers);
    }

    const finalized = await finalizeEdgeExam(attemptId);
    markPendingEdgeResult(attemptId);
    routeToPendingResult();
    return jsonResponse({
      id: attemptId,
      attempt_id: attemptId,
      status: 'submitted',
      queued_for_sync: Boolean(finalized.queued_for_sync),
    });
  }

  return null;
}

export function installEdgeExamFetchBridge(): void {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') return;

  const state = window as typeof window & Record<string, unknown>;
  if (state[PATCH_MARKER]) return;
  state[PATCH_MARKER] = true;

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const matched = matchExamRequest(input);
    if (!matched) return originalFetch(input, init);

    try {
      const response = await handleEdgeRequest(input, init, matched);
      if (response) return response;
    } catch (error) {
      // Une tentative Edge ne doit jamais tomber silencieusement sur l'API
      // centrale : cela pourrait contourner la chaîne locale ou créer un état
      // ambigu. On restitue donc une erreur réseau explicite à l'ExamPage.
      const message = error instanceof Error ? error.message : 'Gateway Edge indisponible';
      return jsonResponse({ detail: message }, 503);
    }

    return originalFetch(input, init);
  };
}

installEdgeExamFetchBridge();
