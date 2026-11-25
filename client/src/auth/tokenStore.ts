import type { TokenStore } from "../api/client";
import type { Tokens } from "../api/types";

export interface KeyValueStorage {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

const KEY = "ryadom.tokens";

export function createTokenStore(storage: KeyValueStorage): TokenStore {
  return {
    async get() {
      const raw = await storage.getItem(KEY);
      if (!raw) return null;
      try {
        const parsed = JSON.parse(raw) as Tokens;
        return parsed.access && parsed.refresh ? parsed : null;
      } catch {
        return null;
      }
    },
    async set(tokens) {
      if (tokens) await storage.setItem(KEY, JSON.stringify(tokens));
      else await storage.removeItem(KEY);
    },
  };
}

export function memoryStorage(): KeyValueStorage {
  const data = new Map<string, string>();
  return {
    async getItem(key) {
      return data.get(key) ?? null;
    },
    async setItem(key, value) {
      data.set(key, value);
    },
    async removeItem(key) {
      data.delete(key);
    },
  };
}
