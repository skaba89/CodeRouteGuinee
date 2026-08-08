import {
  getExamDeviceLabel,
  getOrCreateExamDeviceKey,
  rememberExamDeviceKey,
} from './deviceIdentity';

type ExamStartPayload = {
  booking_reference?: string;
  device_key?: string | null;
  device_label?: string | null;
  [key: string]: unknown;
};

const PATCH_MARKER = '__coderouteExamDeviceFetchBridgeV1';

function isExamStartUrl(input: RequestInfo | URL): boolean {
  const value = typeof input === 'string'
    ? input
    : input instanceof URL
      ? input.toString()
      : input.url;
  return /\/api\/v1\/exams\/start-from-booking(?:\?|$)/.test(value);
}

function resolveMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return init.method.toUpperCase();
  if (typeof Request !== 'undefined' && input instanceof Request) return input.method.toUpperCase();
  return 'GET';
}

export function enrichExamStartPayload(payload: ExamStartPayload): ExamStartPayload {
  const explicitKey = typeof payload.device_key === 'string' ? payload.device_key.trim() : '';
  if (explicitKey) {
    const remembered = rememberExamDeviceKey(explicitKey) ?? explicitKey;
    return {
      ...payload,
      device_key: remembered,
      device_label: payload.device_label || getExamDeviceLabel(remembered),
    };
  }

  const key = getOrCreateExamDeviceKey();
  return {
    ...payload,
    device_key: key,
    device_label: payload.device_label || getExamDeviceLabel(key),
  };
}

export function installExamDeviceFetchBridge(): void {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') return;

  const state = window as typeof window & Record<string, unknown>;
  if (state[PATCH_MARKER]) return;
  state[PATCH_MARKER] = true;

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    if (
      isExamStartUrl(input)
      && resolveMethod(input, init) === 'POST'
      && typeof init?.body === 'string'
    ) {
      try {
        const parsed = JSON.parse(init.body) as ExamStartPayload;
        const enriched = enrichExamStartPayload(parsed);
        return originalFetch(input, {
          ...init,
          body: JSON.stringify(enriched),
        });
      } catch {
        // Un corps non-JSON ou inattendu continue normalement. Le backend
        // conserve son propre contrôle strict et décidera de l'éligibilité.
      }
    }
    return originalFetch(input, init);
  };
}

installExamDeviceFetchBridge();
