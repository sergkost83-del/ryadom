import { API_PREFIX } from "../config";
import { ApiError, buildApiError, networkError } from "./errors";
import type {
  AddressChangeState,
  ChatMessage,
  ChatRoom,
  DirectoryCommunity,
  LegalInfo,
  Notice,
  ProfilePatch,
  RegisterPayload,
  SessionInfo,
  Tokens,
  User,
  VerifyResponse,
} from "./types";

export interface TokenStore {
  get(): Promise<Tokens | null>;
  set(tokens: Tokens | null): Promise<void>;
}

export interface ClientOptions {
  baseUrl: string;
  store: TokenStore;
  fetchImpl?: typeof fetch;
  onSessionExpired?: () => void;
}

interface RequestOptions {
  body?: unknown;
  auth?: boolean;
}

export function createClient(options: ClientOptions) {
  const { baseUrl, store, onSessionExpired } = options;
  const doFetch: typeof fetch = options.fetchImpl ?? ((...args) => fetch(...args));
  let refreshing: Promise<Tokens | null> | null = null;

  async function send(method: string, path: string, body: unknown, access: string | null): Promise<Response> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (access) headers.Authorization = `Bearer ${access}`;
    try {
      return await doFetch(`${baseUrl}${API_PREFIX}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw networkError();
    }
  }

  async function parse(response: Response): Promise<unknown> {
    const text = await response.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }

  /** Обновляет токены. Параллельные запросы ждут один и тот же обмен: токен обновления одноразовый. */
  function refreshTokens(): Promise<Tokens | null> {
    if (refreshing) return refreshing;
    refreshing = (async () => {
      const current = await store.get();
      if (!current) return null;
      const response = await send("POST", "/auth/refresh/", { refresh: current.refresh }, null);
      if (response.ok) {
        const data = (await parse(response)) as { tokens: Tokens };
        await store.set(data.tokens);
        return data.tokens;
      }
      await store.set(null);
      onSessionExpired?.();
      return null;
    })().finally(() => {
      refreshing = null;
    });
    return refreshing;
  }

  async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
    const useAuth = opts.auth !== false;
    const tokens = useAuth ? await store.get() : null;
    let response = await send(method, path, opts.body, tokens?.access ?? null);
    if (response.status === 401 && useAuth && tokens) {
      const fresh = await refreshTokens();
      if (!fresh) throw buildApiError(401, null);
      response = await send(method, path, opts.body, fresh.access);
    }
    const data = await parse(response);
    if (!response.ok) throw buildApiError(response.status, data, response.headers.get("Retry-After"));
    return data as T;
  }

  return {
    request,
    requestCode: (email: string) => request<{ detail: string }>("POST", "/auth/code/request/", { body: { email }, auth: false }),
    verifyCode: (email: string, code: string, deviceName: string) =>
      request<VerifyResponse>("POST", "/auth/code/verify/", { body: { email, code, device_name: deviceName }, auth: false }),
    register: (payload: RegisterPayload) =>
      request<{ tokens: Tokens; user: User }>("POST", "/auth/register/", { body: payload, auth: false }),
    me: () => request<User>("GET", "/me/"),
    updateMe: (patch: ProfilePatch) => request<User>("PATCH", "/me/", { body: patch }),
    communities: () => request<{ communities: DirectoryCommunity[] }>("GET", "/communities/", { auth: false }),
    legal: () => request<LegalInfo>("GET", "/legal/current/", { auth: false }),
    acceptConsents: (consents: Record<string, string>) =>
      request<{ up_to_date: boolean }>("POST", "/me/consents/accept/", { body: { consents } }),
    notices: () => request<{ notices: Notice[] }>("GET", "/notices/"),
    sessions: () => request<{ sessions: SessionInfo[] }>("GET", "/auth/sessions/"),
    revokeSession: (id: string) => request<null>("DELETE", `/auth/sessions/${id}/`),
    logout: () => request<null>("POST", "/auth/logout/"),
    logoutAll: () => request<null>("POST", "/auth/logout-all/"),
    exportData: () => request<Record<string, unknown>>("GET", "/me/export/"),
    deleteAccount: (confirmEmail: string) =>
      request<{ deletion_scheduled_for: string }>("POST", "/me/delete/", { body: { confirm_email: confirmEmail } }),
    addressChange: () => request<AddressChangeState>("GET", "/me/address-change/"),
    requestAddressChange: (payload: { building_id?: string; invite_code?: string }) =>
      request<{ request: NonNullable<AddressChangeState["request"]> }>("POST", "/me/address-change/", { body: payload }),
    cancelAddressChange: () => request<null>("POST", "/me/address-change/cancel/"),
    chatRooms: () => request<{ rooms: ChatRoom[] }>("GET", "/chat/rooms/"),
    chatMessages: (roomId: string) => request<{ messages: ChatMessage[] }>("GET", `/chat/rooms/${roomId}/messages/`),
    sendChatMessage: (roomId: string, body: string) =>
      request<ChatMessage>("POST", `/chat/rooms/${roomId}/messages/`, { body: { body } }),
    deleteChatMessage: (messageId: string) => request<null>("DELETE", `/chat/messages/${messageId}/`),
    reportChatMessage: (messageId: string, reason: string) =>
      request<{ id: string; status: string }>("POST", `/chat/messages/${messageId}/report/`, { body: { reason } }),
    blockChatAuthor: (messageId: string) =>
      request<{ blocked_user_id: string }>("POST", `/chat/messages/${messageId}/block-author/`),
    unblockChatUser: (userId: string) => request<null>("DELETE", `/chat/blocks/${userId}/`),
  };
}

export type ApiClient = ReturnType<typeof createClient>;
export { ApiError };
