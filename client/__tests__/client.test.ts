import { createClient } from "../src/api/client";
import { ApiError } from "../src/api/errors";
import { createTokenStore, memoryStorage } from "../src/auth/tokenStore";
import { fakeFetch, rejection, sampleTokens, sampleUser } from "./helpers";

async function setup(handler: Parameters<typeof fakeFetch>[0], withTokens = true) {
  const store = createTokenStore(memoryStorage());
  if (withTokens) await store.set(sampleTokens("1"));
  const { impl, calls } = fakeFetch(handler);
  let expired = 0;
  const client = createClient({ baseUrl: "https://srv", store, fetchImpl: impl, onSessionExpired: () => (expired += 1) });
  return { client, store, calls, expired: () => expired };
}

describe("запросы к серверу", () => {
  it("подставляет токен доступа и правильный адрес", async () => {
    const { client, calls } = await setup(() => ({ json: sampleUser }));
    const user = await client.me();
    expect(user.email).toBe("a@example.com");
    expect(calls[0].url).toBe("https://srv/api/v1/me/");
    expect(calls[0].headers.Authorization).toBe("Bearer access-1");
  });

  it("публичные запросы идут без токена", async () => {
    const { client, calls } = await setup(() => ({ status: 202, json: { detail: "ok" } }));
    await client.requestCode("a@example.com");
    expect(calls[0].headers.Authorization).toBeUndefined();
    expect(calls[0].body).toEqual({ email: "a@example.com" });
  });

  it("обновляет токены при 401 и повторяет запрос один раз", async () => {
    let meCalls = 0;
    const { client, store, calls } = await setup((call) => {
      if (call.url.endsWith("/auth/refresh/")) return { json: { tokens: sampleTokens("2") } };
      meCalls += 1;
      return meCalls === 1 ? { status: 401, json: { detail: "истёк" } } : { json: sampleUser };
    });
    const user = await client.me();
    expect(user.id).toBe("u1");
    expect(calls.length).toBe(3);
    expect(calls[1].body).toEqual({ refresh: "refresh-1" });
    expect(calls[2].headers.Authorization).toBe("Bearer access-2");
    expect((await store.get())?.refresh).toBe("refresh-2");
  });

  it("параллельные запросы делают только один обмен токена", async () => {
    let refreshCalls = 0;
    const { client } = await setup(async (call) => {
      if (call.url.endsWith("/auth/refresh/")) {
        refreshCalls += 1;
        return { json: { tokens: sampleTokens("2") } };
      }
      return call.headers.Authorization === "Bearer access-2" ? { json: sampleUser } : { status: 401 };
    });
    const results = await Promise.all([client.me(), client.me(), client.me()]);
    expect(results.length).toBe(3);
    expect(refreshCalls).toBe(1);
  });

  it("при отказе обновления очищает токены и сообщает о конце сессии", async () => {
    const { client, store, expired } = await setup((call) =>
      call.url.endsWith("/auth/refresh/") ? { status: 401, json: { detail: "нет" } } : { status: 401 }
    );
    const error = (await rejection(client.me())) as ApiError;
    expect(error.status).toBe(401);
    expect(await store.get()).toBeNull();
    expect(expired()).toBe(1);
  });

  it("сетевой сбой не стирает токены", async () => {
    const { client, store } = await setup(() => ({ throwNetwork: true }));
    const error = (await rejection(client.me())) as ApiError;
    expect(error.status).toBe(0);
    expect((await store.get())?.access).toBe("access-1");
  });

  it("понимает ответ без тела (204)", async () => {
    const { client } = await setup(() => ({ status: 204 }));
    expect(await client.logout()).toBeNull();
  });

  it("превращает ошибку сервера в понятное сообщение", async () => {
    const { client } = await setup(
      () => ({ status: 429, json: { detail: "Слишком много попыток. Повторите позже." }, headers: { "Retry-After": "30" } }),
      false
    );
    const error = (await rejection(client.verifyCode("a@example.com", "123456", "web"))) as ApiError;
    expect(error.status).toBe(429);
    expect(error.retryAfter).toBe(30);
  });

  it("без токена защищённый запрос не пытается обновлять сессию", async () => {
    const { client, calls } = await setup(() => ({ status: 401, json: { detail: "Требуется вход" } }), false);
    const error = (await rejection(client.me())) as ApiError;
    expect(error.status).toBe(401);
    expect(calls.length).toBe(1);
  });
});
