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
      Cookies.remove("access_token");
      window.location.href = "/auth/login";
    }
    return Promise.reject(error);
  }
);

export default api;
