import {
  cleanDisplayName,
  cleanPhone,
  phoneDisplay,
  formatCountdown,
  isInviteCodeComplete,
  isValidCode,
  isValidEmail,
  nameError,
  normalizeCode,
  normalizeEmail,
  normalizeInviteCode,
} from "../src/validation";

describe("e-mail", () => {
  it("приводит к нижнему регистру и убирает пробелы", () => {
    expect(normalizeEmail("  Anna@Example.COM ")).toBe("anna@example.com");
  });
  it("принимает нормальные адреса и отвергает плохие", () => {
    expect(isValidEmail("anna@example.com")).toBe(true);
    expect(isValidEmail("a@b")).toBe(false);
    expect(isValidEmail("без-собаки.ru")).toBe(false);
    expect(isValidEmail("a b@example.com")).toBe(false);
    expect(isValidEmail("")).toBe(false);
  });
});

describe("код из письма", () => {
  it("оставляет только цифры и не больше шести", () => {
    expect(normalizeCode("12 34-56 78")).toBe("123456");
    expect(normalizeCode("abc")).toBe("");
  });
  it("проверяет шесть цифр", () => {
    expect(isValidCode("123456")).toBe(true);
    expect(isValidCode("12345")).toBe(false);
    expect(isValidCode("12345a")).toBe(false);
  });
});

describe("имя", () => {
  it("чистит пробелы", () => {
    expect(cleanDisplayName("  Анна   Иванова ")).toBe("Анна Иванова");
  });
  it("отвергает слишком короткое, длинное и с угловыми скобками", () => {
    expect(nameError("А")).not.toBeNull();
    expect(nameError("x".repeat(61))).not.toBeNull();
    expect(nameError("<b>Анна</b>")).not.toBeNull();
    expect(nameError("Анна")).toBeNull();
  });
});

describe("телефон", () => {
  it("необязателен и нормализуется", () => {
    expect(cleanPhone("")).toBe("");
    expect(cleanPhone("+7 (900) 123-45-67")).toBe("+79001234567");
  });
  it("отвергает неверные номера", () => {
    expect(cleanPhone("abc")).toBeNull();
    expect(cleanPhone("123")).toBeNull();
  });
});

describe("код приглашения", () => {
  it("форматируется как XXXX-XXXX", () => {
    expect(normalizeInviteCode("abcd")).toBe("ABCD");
    expect(normalizeInviteCode("abcdefgh")).toBe("ABCD-EFGH");
    expect(normalizeInviteCode("ab cd-ef!gh999")).toBe("ABCD-EFGH");
  });
  it("определяет полный код", () => {
    expect(isInviteCodeComplete("ABCD-EFGH")).toBe(true);
    expect(isInviteCodeComplete("ABCD-EF")).toBe(false);
  });
});

describe("таймер", () => {
  it("показывает минуты и секунды", () => {
    expect(formatCountdown(65)).toBe("1:05");
    expect(formatCountdown(9)).toBe("0:09");
    expect(formatCountdown(-3)).toBe("0:00");
  });
});

describe("телефон с префиксом +7", () => {
  it("всегда показывает +7 и даёт вводить только 10 цифр", () => {
    expect(phoneDisplay("")).toBe("+7");
    expect(phoneDisplay("+7")).toBe("+7");
    expect(phoneDisplay("+79001234567")).toBe("+79001234567");
    expect(phoneDisplay("89001234567")).toBe("+79001234567");
    expect(phoneDisplay("900123456789999")).toBe("+79001234567");
  });
  it("префикс без цифр считается пустым телефоном", () => {
    expect(cleanPhone("+7")).toBe("");
    expect(cleanPhone("+7 ")).toBe("");
  });
});
