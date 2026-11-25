import type { User } from "../api/types";

export type AuthState = { status: "loading" } | { status: "signedOut" } | { status: "signedIn"; user: User };

export type AuthAction =
  | { type: "loaded"; user: User | null }
  | { type: "signedIn"; user: User }
  | { type: "userUpdated"; user: User }
  | { type: "signedOut" };

export const initialAuthState: AuthState = { status: "loading" };

export function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "loaded":
      return action.user ? { status: "signedIn", user: action.user } : { status: "signedOut" };
    case "signedIn":
      return { status: "signedIn", user: action.user };
    case "userUpdated":
      return state.status === "signedIn" ? { status: "signedIn", user: action.user } : state;
    case "signedOut":
      return { status: "signedOut" };
    default:
      return state;
  }
}
