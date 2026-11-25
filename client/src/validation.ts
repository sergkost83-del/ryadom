// Проверки ввода. Правила совпадают с серверными (сервер всё равно проверяет заново).

export function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

export function isValidEmail(value: string): boolean {
  const email = normalizeEmail(value);
  return email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

export function normalizeCode(value: string): string {
  return value.replace(/\D/g, "").slice(0, 6);
}

export function isValidCode(value: string): boolean {
  return /^\d{6}$/.test(value);
}

export function nameError(value: string): string | null {
  const name = value.split(/\s+/).filter(Boolean).join(" ");
  if (name.length < 2 || name.length > 60) return "Имя: от 2 до 60 символов.";
  if (/[<>]/.test(name)) return "Имя не должно содержать символов < и >.";
  return null;
}

export function cleanDisplayName(value: string): string {
  return value.split(/\s+/).filter(Boolean).join(" ");
}

/** Телефон необязателен. Возвращает нормализованный номер, пустую строку или null, если номер некорректен. */
export function cleanPhone(value: string): string | null {
  const raw = value.replace(/[\s\-()]/g, "");
  if (raw === "") return "";
  return /^\+?[0-9]{10,15}$/.test(raw) ? raw : null;
}

export function normalizeInviteCode(value: string): string {
  const letters = value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
  return letters.length > 4 ? `${letters.slice(0, 4)}-${letters.slice(4)}` : letters;
}

export function isInviteCodeComplete(value: string): boolean {
  return value.replace("-", "").length === 8;
}

export function formatCountdown(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safe / 60);
  const rest = safe % 60;
  return `${minutes}:${rest < 10 ? "0" : ""}${rest}`;
}
