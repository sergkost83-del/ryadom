import { canSendChat, formatChatTime, sanitizeChatBody, CHAT_MAX_LENGTH } from "../src/chat";

describe("текст сообщения", () => {
  it("убирает управляющие символы и пробелы по краям", () => {
    expect(sanitizeChatBody("  привет\x00\x07  ")).toBe("привет");
  });
  it("сохраняет переносы строк и приводит их к единому виду", () => {
    expect(sanitizeChatBody("а\r\nб\rв")).toBe("а\nб\nв");
  });
  it("не пускает пустое сообщение", () => {
    expect(canSendChat("   ")).toBe(false);
    expect(canSendChat("\x00")).toBe(false);
    expect(canSendChat("ок")).toBe(true);
  });
  it("обрезает слишком длинный текст до лимита", () => {
    expect(sanitizeChatBody("x".repeat(CHAT_MAX_LENGTH + 50))).toHaveLength(CHAT_MAX_LENGTH);
  });
  it("оставляет HTML как обычный текст (отображение экранируется на экране)", () => {
    expect(sanitizeChatBody("<b>x</b>")).toBe("<b>x</b>");
  });
});

describe("время сообщения", () => {
  it("сегодняшнее сообщение показывает только время", () => {
    const now = new Date("2026-11-26T12:00:00");
    const sameDay = new Date("2026-11-26T09:05:00").toISOString();
    expect(formatChatTime(sameDay, now)).toMatch(/\d{2}:\d{2}/);
  });
  it("старое сообщение показывает дату", () => {
    const now = new Date("2026-11-26T12:00:00");
    const old = new Date("2026-11-20T09:05:00").toISOString();
    expect(formatChatTime(old, now)).not.toMatch(/:/);
  });
  it("некорректная дата даёт пустую строку", () => {
    expect(formatChatTime("не дата")).toBe("");
  });
});
