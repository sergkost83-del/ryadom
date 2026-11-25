// Адрес сервера. В вебе по умолчанию тот же адрес, с которого открыт сайт (пустая строка).
// Для телефона задаётся при сборке: EXPO_PUBLIC_API_URL=https://example.ru
export const API_BASE: string = (process.env.EXPO_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
export const API_PREFIX = "/api/v1";
