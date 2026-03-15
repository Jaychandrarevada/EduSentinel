// ─────────────────────────────────────────────
//  Axios instance with JWT interceptors
// ─────────────────────────────────────────────
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import Cookies from "js-cookie";

const api = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_URL}/api/v1`,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor: attach Bearer token ──
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor: handle 401 globally ─
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear credentials
      Cookies.remove("access_token");
      localStorage.removeItem("edu_access_token");

      // Update auth store state
      const { useAuthStore } = await import("@/store/authStore");
      useAuthStore.getState().setUnauthenticated();

      // Only redirect if not already on an auth page (prevents loop)
      if (typeof window !== "undefined" &&
          !window.location.pathname.startsWith("/auth")) {
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
