export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;
  retryAfter: number | null;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}, retryAfter: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.retryAfter = retryAfter;
  }
}

const DEFAULT_MESSAGES: Record<number, string> = {
  0: "Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.",
  401: "Нужно войти заново.",
  403: "Нет доступа.",
  404: "Не найдено.",
  409: "Такое действие уже выполнено.",
  429: "Слишком много попыток. Повторите позже.",
  500: "Ошибка на сервере. Мы уже разбираемся, попробуйте позже.",
  503: "Сервис временно недоступен. Попробуйте позже.",
};

function firstString(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = firstString(item);
      if (found) return found;
    }
  }
  return null;
}

/** Превращает ответ сервера об ошибке в ApiError с понятным русским текстом. */
export function buildApiError(status: number, body: unknown, retryAfterHeader: string | null = null): ApiError {
  const retryAfter = retryAfterHeader && /^\d+$/.test(retryAfterHeader) ? Number(retryAfterHeader) : null;
  const fieldErrors: Record<string, string> = {};
  let message: string | null = null;

  if (body && typeof body === "object" && !Array.isArray(body)) {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string") message = record.detail;
    for (const [key, value] of Object.entries(record)) {
      if (key === "detail") continue;
      const text = firstString(value);
      if (text) fieldErrors[key] = text;
    }
    if (!message) message = Object.values(fieldErrors)[0] ?? null;
  }
  if (!message) message = DEFAULT_MESSAGES[status] ?? (status >= 500 ? DEFAULT_MESSAGES[500] : "Что-то пошло не так.");
  if (status === 429 && retryAfter) message = `${message} Подождите ${retryAfter} с.`;
  return new ApiError(status, message, fieldErrors, retryAfter);
}

export function networkError(): ApiError {
  return new ApiError(0, DEFAULT_MESSAGES[0]);
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Что-то пошло не так. Попробуйте ещё раз.";
}
