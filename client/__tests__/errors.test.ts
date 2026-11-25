import { ApiError, buildApiError, errorMessage, networkError } from "../src/api/errors";

describe("разбор ошибок сервера", () => {
  it("берёт текст из detail", () => {
    const error = buildApiError(400, { detail: "Неверный или просроченный код." });
    expect(error.status).toBe(400);
    expect(error.message).toBe("Неверный или просроченный код.");
  });
  it("собирает ошибки полей формы", () => {
    const error = buildApiError(400, { display_name: ["Имя: от 2 до 60 символов."], invite_code: ["Код недействителен."] });
    expect(error.fieldErrors.display_name).toBe("Имя: от 2 до 60 символов.");
    expect(error.fieldErrors.invite_code).toBe("Код недействителен.");
    expect(error.message).toBe("Имя: от 2 до 60 символов.");
  });
  it("добавляет время ожидания при 429", () => {
    const error = buildApiError(429, { detail: "Слишком много попыток. Повторите позже." }, "42");
    expect(error.retryAfter).toBe(42);
    expect(error.message).toContain("42");
  });
  it("подставляет понятный текст, когда тела нет", () => {
    expect(buildApiError(401, null).message).toBe("Нужно войти заново.");
    expect(buildApiError(502, null).message).toContain("Ошибка на сервере");
    expect(buildApiError(418, null).message).toBe("Что-то пошло не так.");
  });
  it("сетевая ошибка имеет статус 0", () => {
    const error = networkError();
    expect(error.status).toBe(0);
    expect(error.message).toContain("Нет связи");
  });
  it("errorMessage работает и для чужих ошибок", () => {
    expect(errorMessage(new ApiError(400, "Текст"))).toBe("Текст");
    expect(errorMessage(new Error("внутренняя"))).toContain("Что-то пошло не так");
  });
});
