import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import type { KeyValueStorage } from "./tokenStore";

interface WebStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** На телефоне токены в защищённом хранилище системы, в вебе — в localStorage. */
export function platformStorage(): KeyValueStorage {
  if (Platform.OS === "web") {
    const local = (globalThis as unknown as { localStorage?: WebStorage }).localStorage;
    return {
      getItem: async (key) => local?.getItem(key) ?? null,
      setItem: async (key, value) => local?.setItem(key, value),
      removeItem: async (key) => local?.removeItem(key),
    };
  }
  return {
    getItem: (key) => SecureStore.getItemAsync(key),
    setItem: (key, value) => SecureStore.setItemAsync(key, value),
    removeItem: (key) => SecureStore.deleteItemAsync(key),
  };
}
