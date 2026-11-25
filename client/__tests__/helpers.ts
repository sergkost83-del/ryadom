// Вспомогательные средства тестов (не тесты): подставной fetch, который записывает вызовы.
export interface FakeCall {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

export interface FakeReply {
  status?: number;
  json?: unknown;
  headers?: Record<string, string>;
  throwNetwork?: boolean;
}

export function fakeFetch(handler: (call: FakeCall) => FakeReply | Promise<FakeReply>) {
  const calls: FakeCall[] = [];
  const impl = (async (input: unknown, init: { method?: string; headers?: Record<string, string>; body?: string } = {}) => {
    const call: FakeCall = {
      url: String(input),
      method: init.method ?? "GET",
      headers: init.headers ?? {},
      body: init.body ? JSON.parse(init.body) : undefined,
    };
    calls.push(call);
    const reply = await handler(call);
    if (reply.throwNetwork) throw new TypeError("Network request failed");
    const status = reply.status ?? 200;
    const text = reply.json === undefined ? "" : JSON.stringify(reply.json);
    return {
      ok: status >= 200 && status < 300,
      status,
      text: async () => text,
      headers: { get: (name: string) => reply.headers?.[name] ?? null },
    };
  }) as unknown as typeof fetch;
  return { impl, calls };
}

export async function rejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("Ожидалась ошибка, но запрос завершился успешно");
}

export const sampleTokens = (suffix = "1") => ({
  token_type: "Bearer",
  access: `access-${suffix}`,
  access_expires_in: 900,
  refresh: `refresh-${suffix}`,
});

export const sampleUser = {
  id: "u1",
  email: "a@example.com",
  display_name: "Анна",
  avatar_id: 1,
  phone: "",
  account_type: "adult",
  consents_up_to_date: true,
  membership: null,
};
