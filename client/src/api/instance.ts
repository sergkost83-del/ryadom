import { Platform } from "react-native";

import { platformStorage } from "../auth/platformStorage";
import { createTokenStore } from "../auth/tokenStore";
import { API_BASE } from "../config";
import { createClient } from "./client";

export const tokenStore = createTokenStore(platformStorage());

let sessionExpiredHandler: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null) {
  sessionExpiredHandler = handler;
}

export const api = createClient({
  baseUrl: API_BASE,
  store: tokenStore,
  onSessionExpired: () => sessionExpiredHandler?.(),
});

export const DEVICE_NAME = `РЯДОМ (${Platform.OS})`;
