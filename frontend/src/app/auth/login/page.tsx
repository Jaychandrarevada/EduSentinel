"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import {
  Eye, EyeOff, AlertCircle, GraduationCap,
  BarChart3, Shield, Brain, CheckCircle2,
} from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { User } from "@/types";
import Cookies from "js-cookie";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type LoginFormData = z.infer<typeof loginSchema>;

const FEATURES = [
  {
    icon: BarChart3,
    title: "Real-time Analytics",
    desc: "Track performance across attendance, grades & engagement in one view.",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    icon: Brain,
    title: "ML Risk Detection",
    desc: "Scikit-learn model flags at-risk students days before they fall behind.",
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  {
    icon: Shield,
    title: "Role-based Access",
    desc: "Admins manage the system; faculty see only their enrolled students.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    icon: GraduationCap,
    title: "Student Profiles",
    desc: "Deep-dive into each student's timeline with risk-factor breakdowns.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { setAuthenticated, status, user } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [activeFeature, setActiveFeature] = useState(0);
  const [loginSuccess, setLoginSuccess] = useState(false);

  // Apply dark background to body so light body style doesn't bleed through
  useEffect(() => {
    document.body.classList.add("dark-page");
    return () => document.body.classList.remove("dark-page");
  }, []);

  // Redirect only when auth check is complete and user is confirmed authenticated
  useEffect(() => {
    if (status !== "authenticated" || !user) return;
    router.replace(user.role === "ADMIN" ? "/dashboard/admin" : "/dashboard/faculty");
  }, [status, user, router]);

  // Cycle feature highlight every 3s
  useEffect(() => {
    const t = setInterval(() => setActiveFeature((i) => (i + 1) % FEATURES.length), 3000);
    return () => clearInterval(t);
  }, []);

  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } =
    useForm<LoginFormData>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      const { data: tokens } = await api.post<{
        access_token: string;
        refresh_token: string;
      }>("/auth/login", { email: data.email, password: data.password });

      Cookies.set("refresh_token", tokens.refresh_token, {
        expires: 7,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
      });

      const { data: me } = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });

      setLoginSuccess(true);
      setAuthenticated(me, tokens.access_token);

      setTimeout(() => {
        router.push(me.role === "ADMIN" ? "/dashboard/admin" : "/dashboard/faculty");
      }, 600);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string }; status?: number } };
      if (e?.response?.status === 401 || e?.response?.status === 400) {
        setServerError("Incorrect email or password.");
      } else if (e?.response?.data?.detail) {
        setServerError(String(e.response.data.detail));
      } else {
        setServerError("Cannot reach the server. Is the backend running?");
      }
    }
  };

  const fillCredentials = (email: string, password: string) => {
    setValue("email", email, { shouldValidate: true });
    setValue("password", password, { shouldValidate: true });
  };

  return (
    <div className="flex min-h-screen bg-slate-950">

      {/* ── LEFT PANEL ───────────────────────────── */}
      <div className="relative hidden lg:flex lg:w-3/5 flex-col justify-between p-12 overflow-hidden">

        {/* Subtle dot grid */}
        <div
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            backgroundImage: "radial-gradient(circle, #6366f1 1px, transparent 1px)",
            backgroundSize: "32px 32px",
          }}
        />
        {/* Gradient overlays */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-slate-950 via-indigo-950/40 to-slate-950" />
        <div className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-violet-600/15 blur-3xl" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/25">
            <Shield className="h-5 w-5 text-white" strokeWidth={2} />
          </div>
          <div>
            <span className="block text-base font-bold text-white tracking-tight">EduSentinel</span>
            <span className="block text-xs text-indigo-300/70">Performance Monitoring</span>
          </div>
        </div>

        {/* Hero */}
        <div className="relative z-10 space-y-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
              <span className="text-xs font-medium text-indigo-300">ML-Powered Early Warning System</span>
            </div>
            <h1 className="text-4xl font-bold text-white leading-tight">
              Catch struggling students{" "}
              <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
                before they fail
              </span>
            </h1>
            <p className="text-slate-400 text-base leading-relaxed max-w-md">
              Unify attendance, exam scores, assignment submissions, and LMS engagement
              into one intelligent monitoring platform.
            </p>
          </div>

          {/* Feature list */}
          <div className="grid gap-3">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              const active = i === activeFeature;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => setActiveFeature(i)}
                  className={`flex items-start gap-4 rounded-2xl border p-4 text-left transition-all duration-300 w-full ${
                    active
                      ? "border-indigo-500/40 bg-indigo-500/10 shadow-lg shadow-indigo-500/10"
                      : "border-slate-800 bg-slate-900/50 hover:border-slate-700"
                  }`}
                >
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${active ? f.bg : "bg-slate-800"}`}>
                    <Icon className={`h-5 w-5 ${active ? f.color : "text-slate-500"}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold ${active ? "text-white" : "text-slate-400"}`}>{f.title}</p>
                    <p className={`text-xs mt-0.5 leading-relaxed ${active ? "text-slate-300" : "text-slate-600"}`}>{f.desc}</p>
                  </div>
                  {active && (
                    <div className="shrink-0 mt-0.5">
                      <CheckCircle2 className="h-4 w-4 text-indigo-400" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Stats bar */}
        <div className="relative z-10 flex items-center gap-8 rounded-2xl border border-slate-800 bg-slate-900/60 px-6 py-4 backdrop-blur-sm">
          {[
            { val: "20+", label: "Students tracked" },
            { val: "3", label: "Active courses" },
            { val: "99%", label: "API uptime" },
            { val: "< 1s", label: "Alert latency" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-lg font-bold text-white">{s.val}</p>
              <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── RIGHT PANEL ──────────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-16 bg-slate-950 lg:bg-slate-900/50 lg:border-l lg:border-slate-800">

        {/* Mobile logo */}
        <div className="mb-8 flex items-center gap-3 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-bold text-white">EduSentinel</span>
        </div>

        <div className="w-full max-w-sm">

          {/* Heading */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white">Sign in</h2>
            <p className="mt-1.5 text-sm text-slate-400">
              Enter your credentials to access the dashboard
            </p>
          </div>

          {/* Success state */}
          {loginSuccess && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <p className="text-sm font-medium text-emerald-300">Login successful! Redirecting…</p>
            </div>
          )}

          {/* Error banner */}
          {serverError && !loginSuccess && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 animate-fade-in">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
              <p className="text-sm text-red-300">{serverError}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">

            {/* Email */}
            <div className="space-y-1.5">
              <label htmlFor="email" className="block text-sm font-medium text-slate-300">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@institution.edu"
                className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                  errors.email
                    ? "border-red-500/60 focus:ring-red-500/20"
                    : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                }`}
                {...register("email")}
              />
              {errors.email && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label htmlFor="password" className="block text-sm font-medium text-slate-300">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 pr-12 text-sm text-white placeholder-slate-600 outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                    errors.password
                      ? "border-red-500/60 focus:ring-red-500/20"
                      : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                  }`}
                  {...register("password")}
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide" : "Show"}
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting || loginSuccess}
              className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:from-indigo-500 hover:to-violet-500 hover:shadow-indigo-500/30 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Signing in…
                </span>
              ) : loginSuccess ? (
                <span className="flex items-center justify-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Redirecting…
                </span>
              ) : (
                "Sign in →"
              )}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-px flex-1 bg-slate-800" />
              <span className="text-xs font-medium text-slate-600 uppercase tracking-wider">Demo accounts</span>
              <div className="h-px flex-1 bg-slate-800" />
            </div>
            <div className="space-y-2">
              {[
                { role: "Admin", email: "admin@edusentinel.dev", password: "Admin@123", color: "text-violet-400", bg: "hover:border-violet-500/40 hover:bg-violet-500/5" },
                { role: "Faculty", email: "faculty@edusentinel.dev", password: "Faculty@123", color: "text-blue-400", bg: "hover:border-blue-500/40 hover:bg-blue-500/5" },
              ].map((cred) => (
                <button
                  key={cred.role}
                  type="button"
                  onClick={() => fillCredentials(cred.email, cred.password)}
                  className={`flex w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left transition-all duration-150 ${cred.bg}`}
                >
                  <div>
                    <span className={`text-xs font-bold uppercase tracking-wide ${cred.color}`}>{cred.role}</span>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">{cred.email}</p>
                  </div>
                  <span className="text-xs text-slate-600 font-mono bg-slate-800 px-2 py-1 rounded-lg">
                    click to fill
                  </span>
                </button>
              ))}
            </div>
          </div>

          <p className="mt-6 text-center text-sm text-slate-500">
            New faculty member?{" "}
            <a href="/auth/faculty-register" className="font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
              Create an account
            </a>
          </p>
          <p className="mt-3 text-center text-xs text-slate-700">
            © {new Date().getFullYear()} EduSentinel · Access restricted to authorised users
          </p>
        </div>
      </div>
    </div>
  );
}
