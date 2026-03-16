"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Database, Zap, CheckCircle2, AlertCircle,
  Users, TrendingUp, TrendingDown, Minus,
  Trash2, AlertTriangle, X,
} from "lucide-react";
import api from "@/lib/api";
import { GenerateStudentsResponse } from "@/types";

// ── Generate form ──────────────────────────────────────────────────────────────
const schema = z.object({
  num_students: z.coerce.number().min(300, "Minimum 300").max(2000, "Maximum 2000"),
  semester: z.string().min(3).max(20),
});
type FormData = z.infer<typeof schema>;

// ── Reset mode ────────────────────────────────────────────────────────────────
type ResetMode = "last_n" | "keep_first_n" | "generated_all";

const RESET_MODES: { value: ResetMode; label: string; description: string; needsCount: boolean }[] = [
  {
    value: "last_n",
    label: "Delete last N students",
    description: "Removes the most recently generated N students (highest IDs).",
    needsCount: true,
  },
  {
    value: "keep_first_n",
    label: "Keep only first N students",
    description: "Keeps the oldest N students and deletes everyone else.",
    needsCount: true,
  },
  {
    value: "generated_all",
    label: "Delete all generated students",
    description: "Deletes every student with a GEN roll number (all synthetic data).",
    needsCount: false,
  },
];

export default function GenerateDataPage() {
  const [result, setResult] = useState<GenerateStudentsResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  // Reset state
  const [resetMode, setResetMode] = useState<ResetMode>("last_n");
  const [resetCount, setResetCount] = useState<string>("300");
  const [resetConfirm, setResetConfirm] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetResult, setResetResult] = useState<{ deleted: number; message: string } | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<FormData>({
      resolver: zodResolver(schema),
      defaultValues: { num_students: 500, semester: "2025-ODD" },
    });

  const onSubmit = async (data: FormData) => {
    setGenError(null);
    setResult(null);
    try {
      const { data: res } = await api.post<GenerateStudentsResponse>("/students/generate", data);
      setResult(res);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } } };
      const detail = e?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? (detail as { msg?: string }[]).map((d) => d.msg ?? JSON.stringify(d)).join("; ")
          : "Generation failed. Check backend logs.";
      setGenError(msg);
    }
  };

  async function handleReset() {
    const modeInfo = RESET_MODES.find((m) => m.value === resetMode)!;
    const count = modeInfo.needsCount ? parseInt(resetCount, 10) : undefined;
    if (modeInfo.needsCount && (!count || count < 1)) {
      setResetError("Please enter a valid number.");
      return;
    }
    setResetLoading(true);
    setResetError(null);
    setResetResult(null);
    try {
      const params: Record<string, string | number> = { mode: resetMode };
      if (count !== undefined) params.count = count;
      const { data } = await api.post("/admin/reset-students", null, { params });
      setResetResult({ deleted: data.students_deleted, message: data.message });
      setResetConfirm(false);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } } };
      const detail = e?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? (detail as { msg?: string }[]).map((d) => d.msg ?? JSON.stringify(d)).join("; ")
          : "Reset failed. Check backend logs.";
      setResetError(msg);
    } finally {
      setResetLoading(false);
    }
  }

  const SEMESTERS = ["2024-EVEN", "2024-ODD", "2025-EVEN", "2025-ODD", "2026-EVEN"];
  const selectedMode = RESET_MODES.find((m) => m.value === resetMode)!;

  return (
    <div className="space-y-8 max-w-2xl">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100">
          <Database className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Student Data Generator</h1>
          <p className="text-sm text-gray-500">Populate the database with realistic synthetic student data</p>
        </div>
      </div>

      {/* ── Generate form ────────────────────────────────────────────────── */}
      <div className="card p-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Number of Students
              <span className="ml-1.5 text-xs font-normal text-gray-400">(300 – 2000)</span>
            </label>
            <input
              type="number"
              className="input"
              placeholder="500"
              {...register("num_students")}
            />
            {errors.num_students && (
              <p className="mt-1 flex items-center gap-1 text-xs text-red-500">
                <AlertCircle className="h-3 w-3" /> {errors.num_students.message}
              </p>
            )}
            <div className="mt-2 flex gap-2">
              {[300, 500, 1000, 1500, 2000].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => (document.querySelector("input[type=number]") as HTMLInputElement).value = String(n)}
                  className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-500 hover:border-indigo-300 hover:text-indigo-600 transition-all"
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Semester</label>
            <select className="input" {...register("semester")}>
              {SEMESTERS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="rounded-xl bg-gray-50 p-4 space-y-2">
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Generated Distribution</p>
            <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
              <div>• Attendance: N(75%, σ=15)</div>
              <div>• IA scores: N(65%, σ=18)</div>
              <div>• Assignment: N(70%, σ=16)</div>
              <div>• LMS activity: N(60%, σ=22)</div>
              <div>• Previous GPA: N(6.5, σ=1.5)</div>
              <div>• Names: Faker (en_IN locale)</div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3"
          >
            <Zap className="h-4 w-4" />
            {isSubmitting ? "Generating…" : "Generate Students"}
          </button>
        </form>
      </div>

      {genError && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-500" />
          <p className="text-sm text-red-700">{genError}</p>
        </div>
      )}

      {result && (
        <div className="card p-6 animate-fade-in">
          <div className="flex items-center gap-3 mb-5">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            <h2 className="font-semibold text-gray-900">Generation Complete</h2>
          </div>
          <p className="text-sm text-gray-500 mb-5">{result.message}</p>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl bg-indigo-50 p-4 flex items-center gap-3">
              <Users className="h-8 w-8 text-indigo-500" />
              <div>
                <p className="text-xs text-indigo-600 font-medium">Total Created</p>
                <p className="text-2xl font-bold text-indigo-700">{result.students_created}</p>
              </div>
            </div>
            <div className="rounded-xl bg-gray-50 p-4 flex items-center gap-3">
              <Minus className="h-6 w-6 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500 font-medium">Semester</p>
                <p className="text-lg font-bold text-gray-700">{result.semester}</p>
              </div>
            </div>
            <div className="rounded-xl bg-red-50 p-4 flex items-center gap-3">
              <TrendingDown className="h-6 w-6 text-red-500" />
              <div>
                <p className="text-xs text-red-600 font-medium">High Risk</p>
                <p className="text-2xl font-bold text-red-600">{result.high_risk}</p>
                <p className="text-xs text-red-400">
                  {((result.high_risk / result.students_created) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
            <div className="rounded-xl bg-amber-50 p-4 flex items-center gap-3">
              <TrendingUp className="h-6 w-6 text-amber-500" />
              <div>
                <p className="text-xs text-amber-600 font-medium">Medium Risk</p>
                <p className="text-2xl font-bold text-amber-600">{result.medium_risk}</p>
                <p className="text-xs text-amber-400">
                  {((result.medium_risk / result.students_created) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
          <div className="mt-4 rounded-xl bg-emerald-50 p-4 flex items-center gap-3">
            <CheckCircle2 className="h-6 w-6 text-emerald-500" />
            <div>
              <p className="text-xs text-emerald-600 font-medium">Low Risk (Safe)</p>
              <p className="text-2xl font-bold text-emerald-600">
                {result.students_created - result.high_risk - result.medium_risk}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Divider ──────────────────────────────────────────────────────── */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-gray-50 px-3 text-xs font-medium text-gray-400 uppercase tracking-wide">
            Reset / Delete Students
          </span>
        </div>
      </div>

      {/* ── Reset section ────────────────────────────────────────────────── */}
      <div className="card border-red-100 p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-100">
            <Trash2 className="h-4 w-4 text-red-600" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Reset Students</h2>
            <p className="text-xs text-gray-400">
              Remove a batch of generated students and all their related data.
            </p>
          </div>
        </div>

        {/* Mode selector */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-600">Select what to delete</p>
          <div className="space-y-2">
            {RESET_MODES.map((m) => (
              <label
                key={m.value}
                className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-all ${
                  resetMode === m.value
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <input
                  type="radio"
                  name="resetMode"
                  value={m.value}
                  checked={resetMode === m.value}
                  onChange={() => { setResetMode(m.value); setResetError(null); setResetResult(null); }}
                  className="mt-0.5 accent-red-600"
                />
                <div>
                  <p className={`text-sm font-medium ${resetMode === m.value ? "text-red-800" : "text-gray-700"}`}>
                    {m.label}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">{m.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Count input */}
        {selectedMode.needsCount && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              {resetMode === "last_n" ? "Number of students to delete" : "Number of students to keep"}
            </label>
            <input
              type="number"
              min={1}
              value={resetCount}
              onChange={(e) => setResetCount(e.target.value)}
              placeholder="e.g. 300"
              className="input"
            />
            <div className="mt-2 flex gap-2">
              {[100, 300, 500, 1000, 1500].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setResetCount(String(n))}
                  className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-500 hover:border-red-300 hover:text-red-600 transition-all"
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Warning box */}
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-500" />
          <p className="text-xs text-amber-700">
            This permanently deletes the students and all their attendance, marks, assignments,
            LMS activity, predictions, and alerts. This cannot be undone.
          </p>
        </div>

        {/* Confirm dialog */}
        {resetConfirm ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-3">
            <p className="text-sm font-semibold text-red-800">Are you sure?</p>
            <p className="text-xs text-red-600">
              You are about to {resetMode === "keep_first_n"
                ? `delete all students except the first ${resetCount}`
                : resetMode === "last_n"
                  ? `delete the last ${resetCount} students`
                  : "delete ALL generated students (GEN roll numbers)"}
              . All their data will be permanently removed.
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleReset}
                disabled={resetLoading}
                className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                {resetLoading ? "Deleting…" : "Yes, delete permanently"}
              </button>
              <button
                onClick={() => setResetConfirm(false)}
                disabled={resetLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => { setResetError(null); setResetResult(null); setResetConfirm(true); }}
            className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            Reset Students…
          </button>
        )}

        {/* Reset error */}
        {resetError && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-500" />
            <p className="text-sm text-red-700">{resetError}</p>
          </div>
        )}

        {/* Reset success */}
        {resetResult && (
          <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
            <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-emerald-500" />
            <div>
              <p className="text-sm font-semibold text-emerald-800">
                Deleted {resetResult.deleted} student{resetResult.deleted !== 1 ? "s" : ""}
              </p>
              <p className="text-xs text-emerald-600 mt-0.5">{resetResult.message}</p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
