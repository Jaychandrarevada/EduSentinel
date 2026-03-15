"use client";

// ─────────────────────────────────────────────────────────────────────────────
//  AuthProvider
//  Runs once on app mount. Reads the token from localStorage, calls /auth/me
//  to verify it, then sets the auth status to 'authenticated' or 'unauthenticated'.
//  Until the check completes, status stays 'initializing' — no redirects happen.
// ─────────────────────────────────────────────────────────────────────────────
import { useEffect } from "react";
import { useAuthStore, TOKEN_STORAGE_KEY } from "@/store/authStore";
import type { User } from "@/types";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setAuthenticated, setUnauthenticated } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);

    if (!token) {
      setUnauthenticated();
      return;
    }

    // Verify the stored token is still valid
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
    fetch(`${apiBase}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("invalid");
        return res.json() as Promise<User>;
      })
      .then((user) => setAuthenticated(user, token))
      .catch(() => setUnauthenticated());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <>{children}</>;
}
