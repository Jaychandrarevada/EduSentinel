// ─────────────────────────────────────────────
//  Zustand auth store
// ─────────────────────────────────────────────
import { create } from "zustand";
import { persist } from "zustand/middleware";
import Cookies from "js-cookie";
import { User } from "@/types";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setUser(user, token) {
        Cookies.set("access_token", token, {
          expires: 1 / 24, // 1 hour
          secure: process.env.NODE_ENV === "production",
          sameSite: "strict",
        });
        set({ user, isAuthenticated: true });
      },

      logout() {
        Cookies.remove("access_token");
        set({ user: null, isAuthenticated: false });
      },
    }),
    { name: "auth-store" }
  )
);
