import { authReducer, initialAuthState } from "../src/auth/authReducer";
import { createTokenStore, memoryStorage } from "../src/auth/tokenStore";
import { sampleTokens, sampleUser } from "./helpers";

describe("состояние входа", () => {
  it("начинается с загрузки", () => {
    expect(initialAuthState.status).toBe("loading");
  });
  it("после загрузки без пользователя — вышел", () => {
    expect(authReducer(initialAuthState, { type: "loaded", user: null }).status).toBe("signedOut");
  });
  it("после загрузки с пользователем — вошёл", () => {
    const state = authReducer(initialAuthState, { type: "loaded", user: sampleUser });
    expect(state.status).toBe("signedIn");
  });
  it("обновление данных меняет пользователя только у вошедшего", () => {
    const signedOut = authReducer({ status: "signedOut" }, { type: "userUpdated", user: sampleUser });
    expect(signedOut.status).toBe("signedOut");
    const signedIn = authReducer({ status: "signedIn", user: sampleUser }, { type: "userUpdated", user: { ...sampleUser, display_name: "Новое" } });
    expect(signedIn.status === "signedIn" && signedIn.user.display_name).toBe("Новое");
  });
  it("выход сбрасывает состояние", () => {
    expect(authReducer({ status: "signedIn", user: sampleUser }, { type: "signedOut" }).status).toBe("signedOut");
  });
});

describe("хранилище токенов", () => {
  it("сохраняет, читает и стирает", async () => {
    const store = createTokenStore(memoryStorage());
    expect(await store.get()).toBeNull();
    await store.set(sampleTokens("7"));
    expect((await store.get())?.refresh).toBe("refresh-7");
    await store.set(null);
    expect(await store.get()).toBeNull();
  });
  it("повреждённые данные считает отсутствием токенов", async () => {
    const storage = memoryStorage();
    await storage.setItem("ryadom.tokens", "{не json");
    expect(await createTokenStore(storage).get()).toBeNull();
    await storage.setItem("ryadom.tokens", JSON.stringify({ access: "" }));
    expect(await createTokenStore(storage).get()).toBeNull();
  });
});
