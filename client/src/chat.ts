// Чистые функции для чатов: без React, проверяются тестами.
export const CHAT_MAX_LENGTH = 1000;

/** Убирает управляющие символы (кроме переноса строки) и пробелы по краям. Пустой текст даёт пустую строку. */
export function sanitizeChatBody(value: string): string {
  const kept = Array.from(value || "")
    .filter((ch) => ch === "\n" || ch === "\r" || !/\p{Cc}/u.test(ch))
    .join("");
  return kept.replace(/\r\n?/g, "\n").trim().slice(0, CHAT_MAX_LENGTH);
}

export function canSendChat(value: string): boolean {
  return sanitizeChatBody(value).length > 0;
}

/** Время сообщения: «14:05», а для более старых дат — день и месяц. */
export function formatChatTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay) {
    return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}
