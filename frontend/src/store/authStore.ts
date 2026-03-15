// ─────────────────────────────────────────────
//  Auth store — NO persist middleware
//  Token lives in localStorage; status is derived
//  on every page load by AuthProvider via /auth/me
// ─────────────────────────────────────────────
import { create } from "zustand";
import Cookies from "js-cookie";
import { User } from "@/types";

export type AuthStatus = "initializing" | "authenticated" | "unauthenticated";

interface AuthState {
  user: User | null;
  status: AuthStatus;
  setAuthenticated: (user: User, token: string) => void;
  setUnauthenticated: () => void;
  logout: () => void; // alias for setUnauthenticated, used by Sidebar
}

const TOKEN_KEY = "edu_access_token";

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  status: "initializing",

  setAuthenticated(user, token) {
    localStorage.setItem(TOKEN_KEY, token);
    Cookies.set("access_token", token, {
      expires: 1 / 24,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
    });
    set({ user, status: "authenticated" });
  },

  setUnauthenticated() {
    localStorage.removeItem(TOKEN_KEY);
    Cookies.remove("access_token");
    set({ user: null, status: "unauthenticated" });
  },

  logout() {
    localStorage.removeItem(TOKEN_KEY);
    Cookies.remove("access_token");
    set({ user: null, status: "unauthenticated" });
  },
}));

export const TOKEN_STORAGE_KEY = TOKEN_KEY;
