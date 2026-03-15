"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Eye, EyeOff, AlertCircle, Shield, GraduationCap, CheckCircle2, ArrowLeft,
} from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { User } from "@/types";
import Cookies from "js-cookie";

const schema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
  department: z.string().min(2, "Department is required"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Must contain at least one uppercase letter")
    .regex(/[0-9]/, "Must contain at least one number"),
  confirm_password: z.string().min(1, "Please confirm your password"),
}).refine((d) => d.password === d.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});

type FormData = z.infer<typeof schema>;

const DEPARTMENTS = [
  "Computer Science", "Electronics", "Mechanical", "Civil",
  "Chemical", "Information Technology", "Mathematics", "Physics",
  "Business Administration", "Other",
];

export default function FacultyRegisterPage() {
  const router = useRouter();
  const { setUser } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    document.body.classList.add("dark-page");
    return () => document.body.classList.remove("dark-page");
  }, []);

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setServerError(null);
    try {
      const { data: tokens } = await api.post<{
        access_token: string; refresh_token: string;
      }>("/auth/faculty-register", {
        full_name: data.full_name,
        email: data.email,
        department: data.department,
        password: data.password,
        role: "FACULTY",
      });

      Cookies.set("refresh_token", tokens.refresh_token, {
        expires: 7, secure: process.env.NODE_ENV === "production", sameSite: "strict",
      });

      const { data: me } = await api.get<User>("/auth/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });

      setSuccess(true);
      setUser(me, tokens.access_token);
      setTimeout(() => router.push("/dashboard/faculty"), 1200);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string }; status?: number } };
      if (e?.response?.status === 409) {
        setServerError("An account with this email already exists. Try logging in.");
      } else if (e?.response?.data?.detail) {
        setServerError(String(e.response.data.detail));
      } else {
        setServerError("Registration failed. Please try again.");
      }
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-950">

      {/* ── LEFT PANEL ── */}
      <div className="relative hidden lg:flex lg:w-2/5 flex-col justify-between p-12 overflow-hidden">
        <div className="pointer-events-none absolute inset-0 opacity-25"
          style={{ backgroundImage: "radial-gradient(circle, #6366f1 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-slate-950 via-indigo-950/40 to-slate-950" />
        <div className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="block text-base font-bold text-white">EduSentinel</span>
            <span className="block text-xs text-indigo-300/70">Performance Monitoring</span>
          </div>
        </div>

        {/* Content */}
        <div className="relative z-10 space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1">
            <GraduationCap className="h-3.5 w-3.5 text-indigo-400" />
            <span className="text-xs font-medium text-indigo-300">Faculty Portal</span>
          </div>
          <h1 className="text-3xl font-bold text-white leading-tight">
            Join as a Faculty{" "}
            <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
              Member
            </span>
          </h1>
          <p className="text-slate-400 text-sm leading-relaxed">
            Create your faculty account to monitor student performance, receive at-risk
            alerts, and access ML-powered insights for your courses.
          </p>

          <div className="space-y-3 pt-2">
            {[
              "Monitor your enrolled students in real time",
              "Receive instant alerts when students are at risk",
              "View ML-powered risk predictions and SHAP insights",
              "Export student performance reports as CSV",
            ].map((item) => (
              <div key={item} className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                <span className="text-sm text-slate-300">{item}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-xs text-slate-700">
          © {new Date().getFullYear()} EduSentinel · Secure Faculty Portal
        </p>
      </div>

      {/* ── RIGHT PANEL ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-16 bg-slate-950 lg:bg-slate-900/50 lg:border-l lg:border-slate-800">

        <div className="w-full max-w-sm">
          {/* Back to login */}
          <Link
            href="/auth/login"
            className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to login
          </Link>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white">Create Faculty Account</h2>
            <p className="mt-1.5 text-sm text-slate-400">
              Fill in your details to register as a faculty member.
            </p>
          </div>

          {/* Success */}
          {success && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <p className="text-sm font-medium text-emerald-300">Account created! Redirecting to dashboard…</p>
            </div>
          )}

          {/* Error */}
          {serverError && !success && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
              <p className="text-sm text-red-300">{serverError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">

            {/* Full Name */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-300">Full Name</label>
              <input
                type="text"
                autoComplete="name"
                placeholder="Dr. Jane Smith"
                className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                  errors.full_name ? "border-red-500/60 focus:ring-red-500/20" : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                }`}
                {...register("full_name")}
              />
              {errors.full_name && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />{errors.full_name.message}
                </p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-300">Email address</label>
              <input
                type="email"
                autoComplete="email"
                placeholder="you@institution.edu"
                className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                  errors.email ? "border-red-500/60 focus:ring-red-500/20" : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                }`}
                {...register("email")}
              />
              {errors.email && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />{errors.email.message}
                </p>
              )}
            </div>

            {/* Department */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-300">Department</label>
              <select
                className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 text-sm text-white outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                  errors.department ? "border-red-500/60 focus:ring-red-500/20" : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                }`}
                {...register("department")}
                defaultValue=""
              >
                <option value="" disabled className="bg-slate-800 text-slate-500">Select your department…</option>
                {DEPARTMENTS.map((d) => (
                  <option key={d} value={d} className="bg-slate-800 text-white">{d}</option>
                ))}
              </select>
              {errors.department && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />{errors.department.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-300">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Min 8 chars, 1 uppercase, 1 number"
                  className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 pr-12 text-sm text-white placeholder-slate-600 outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                    errors.password ? "border-red-500/60 focus:ring-red-500/20" : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                  }`}
                  {...register("password")}
                />
                <button type="button" onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-500 hover:text-slate-300 transition-colors">
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />{errors.password.message}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-300">Confirm Password</label>
              <div className="relative">
                <input
                  type={showConfirm ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  className={`w-full rounded-xl border bg-slate-800/60 px-4 py-3 pr-12 text-sm text-white placeholder-slate-600 outline-none transition-all focus:bg-slate-800 focus:ring-2 ${
                    errors.confirm_password ? "border-red-500/60 focus:ring-red-500/20" : "border-slate-700 focus:border-indigo-500/70 focus:ring-indigo-500/20"
                  }`}
                  {...register("confirm_password")}
                />
                <button type="button" onClick={() => setShowConfirm(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-500 hover:text-slate-300 transition-colors">
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="h-3 w-3" />{errors.confirm_password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting || success}
              className="mt-2 w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Creating account…
                </span>
              ) : success ? (
                <span className="flex items-center justify-center gap-2">
                  <CheckCircle2 className="h-4 w-4" /> Account created!
                </span>
              ) : (
                "Create Faculty Account →"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link href="/auth/login" className="font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
