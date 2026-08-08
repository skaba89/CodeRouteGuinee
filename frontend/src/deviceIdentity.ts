const EXAM_DEVICE_KEY_STORAGE = 'coderoute:exam-device-key:v1';

function fallbackId(): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `${Date.now().toString(36)}-${random}`;
}

export function rememberExamDeviceKey(value: string): string | null {
  const normalized = value.trim().slice(0, 160);
  if (normalized.length < 4) return null;
  try {
    window.localStorage.setItem(EXAM_DEVICE_KEY_STORAGE, normalized);
  } catch {
    // Le stockage navigateur peut être bloqué ; l'appel courant reste valide.
  }
  return normalized;
}

export function getOrCreateExamDeviceKey(): string {
  try {
    const existing = window.localStorage.getItem(EXAM_DEVICE_KEY_STORAGE)?.trim();
    if (existing) return existing;

    const uuid = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : fallbackId();
    const key = `CRG-STATION-${uuid}`.slice(0, 160);
    window.localStorage.setItem(EXAM_DEVICE_KEY_STORAGE, key);
    return key;
  } catch {
    // Les navigateurs très verrouillés peuvent refuser localStorage. Le serveur
    // acceptera ce poste seulement si le centre n'a pas encore activé son registre.
    return `CRG-STATION-TEMP-${fallbackId()}`.slice(0, 160);
  }
}

export function getExamDeviceLabel(deviceKey?: string): string {
  const key = deviceKey?.trim() || getOrCreateExamDeviceKey();
  return `Poste CodeRoute ${key.slice(-8).toUpperCase()}`;
}

export async function copyExamDeviceKey(): Promise<boolean> {
  const key = getOrCreateExamDeviceKey();
  try {
    await navigator.clipboard.writeText(key);
    return true;
  } catch {
    return false;
  }
}
