import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, type ReactNode } from "react";

import { api, setSessionExpiredHandler, tokenStore } from "../api/instance";
import type { Tokens, User } from "../api/types";
import { flow } from "../flow";
import { authReducer, initialAuthState, type AuthState } from "./authReducer";

interface AuthContextValue {
  state: AuthState;
  signIn(tokens: Tokens, user: User): Promise<void>;
  signOut(): Promise<void>;
  refreshUser(): Promise<User | null>;
  setUser(user: User): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialAuthState);

  useEffect(() => {
    let cancelled = false;
    setSessionExpiredHandler(() => dispatch({ type: "signedOut" }));
    (async () => {
      const tokens = await tokenStore.get();
      if (!tokens) {
        if (!cancelled) dispatch({ type: "loaded", user: null });
        return;
      }
      try {
        const user = await api.me();
        if (!cancelled) dispatch({ type: "loaded", user });
      } catch {
        if (!cancelled) dispatch({ type: "loaded", user: null });
      }
    })();
    return () => {
      cancelled = true;
      setSessionExpiredHandler(null);
    };
  }, []);

  const signIn = useCallback(async (tokens: Tokens, user: User) => {
    await tokenStore.set(tokens);
    dispatch({ type: "signedIn", user });
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // выход должен сработать, даже если сервер недоступен
    }
    await tokenStore.set(null);
    flow.reset();
    dispatch({ type: "signedOut" });
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const user = await api.me();
      dispatch({ type: "userUpdated", user });
      return user;
    } catch {
      return null;
    }
  }, []);

  const setUser = useCallback((user: User) => dispatch({ type: "userUpdated", user }), []);

  const value = useMemo(() => ({ state, signIn, signOut, refreshUser, setUser }), [state, signIn, signOut, refreshUser, setUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth нужно вызывать внутри AuthProvider");
  return value;
}
