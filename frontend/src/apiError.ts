export type ApiValidationError = {
  field: string;
  message: string;
};

function asNonEmptyString(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const normalized = value.trim();
  return normalized || undefined;
}

function normalizeValidationErrors(value: unknown): ApiValidationError[] {
  if (!Array.isArray(value)) return [];

  return value
    .map((item): ApiValidationError | null => {
      if (!item || typeof item !== 'object') return null;
      const record = item as Record<string, unknown>;
      const field = asNonEmptyString(record.field) ?? 'champ';
      const message = asNonEmptyString(record.message) ?? asNonEmptyString(record.msg);
      if (!message) return null;
      return { field, message };
    })
    .filter((item): item is ApiValidationError => item !== null)
    .slice(0, 5);
}

function detailMessage(detail: unknown): { message?: string; code?: string } {
  if (typeof detail === 'string') {
    return { message: asNonEmptyString(detail) };
  }

  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) {
    return {};
  }

  const record = detail as Record<string, unknown>;
  return {
    message: asNonEmptyString(record.message) ?? asNonEmptyString(record.detail),
    code: asNonEmptyString(record.code),
  };
}

export class ApiError extends Error {
  status: number;
  code?: string;
  validationErrors: ApiValidationError[];

  constructor(
    status: number,
    message: string,
    options: { code?: string; validationErrors?: ApiValidationError[] } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = options.code;
    this.validationErrors = options.validationErrors ?? [];
  }
}

export async function buildApiError(response: Response): Promise<ApiError> {
  const fallback = `API error ${response.status}`;

  try {
    const payload: unknown = await response.json();
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return new ApiError(response.status, fallback);
    }

    const record = payload as Record<string, unknown>;
    const detail = detailMessage(record.detail);
    const topLevelMessage = asNonEmptyString(record.message);
    const validationErrors = normalizeValidationErrors(record.errors);

    let message = detail.message ?? topLevelMessage ?? fallback;
    if (validationErrors.length > 0) {
      const summary = validationErrors
        .map((error) => `${error.field} : ${error.message}`)
        .join(' ; ');
      message = `${message} — ${summary}`;
    }

    return new ApiError(response.status, message, {
      code: detail.code ?? asNonEmptyString(record.code),
      validationErrors,
    });
  } catch {
    // A non-JSON error response must remain deterministic and never expose raw HTML/text.
    return new ApiError(response.status, fallback);
  }
}
