"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Database, Zap, CheckCircle2, AlertCircle,
  Users, TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import api from "@/lib/api";
import { GenerateStudentsResponse } from "@/types";

const schema = z.object({
  num_students: z.coerce.number().min(300, "Minimum 300").max(2000, "Maximum 2000"),
  semester: z.string().min(3).max(20),
});
type FormData = z.infer<typeof schema>;

export default function GenerateDataPage() {
  const [result, setResult] = useState<GenerateStudentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<FormData>({
      resolver: zodResolver(schema),
      defaultValues: { num_students: 500, semester: "2025-ODD" },
    });

  const onSubmit = async (data: FormData) => {
    setError(null);
    setResult(null);
    try {
      const { data: res } = await api.post<GenerateStudentsResponse>("/students/generate", data);
      setResult(res);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? "Generation failed. Check backend logs.");
    }
  };

  const SEMESTERS = ["2024-EVEN", "2024-ODD", "2025-EVEN", "2025-ODD", "2026-EVEN"];

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100">
          <Database className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Student Data Generator</h1>
          <p className="text-sm text-gray-500">Populate the database with realistic synthetic student data</p>
        </div>
      </div>

      {/* Form card */}
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
            {/* Preset buttons */}
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
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Semester
            </label>
            <select className="input" {...register("semester")}>
              {SEMESTERS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {errors.semester && (
              <p className="mt-1 flex items-center gap-1 text-xs text-red-500">
                <AlertCircle className="h-3 w-3" /> {errors.semester.message}
              </p>
            )}
          </div>

          {/* Data distribution info */}
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

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Result */}
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
          <p className="mt-4 text-xs text-gray-400">
            Students are now in the database. Navigate to <strong>Students</strong> to view them or trigger a prediction run from <strong>ML Config</strong>.
          </p>
        </div>
      )}
    </div>
  );
}
