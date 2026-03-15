"use client";

import { useState } from "react";
import { Download, CheckCircle2, AlertCircle, Filter, FileText, Clock } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

interface ExportOptions {
  semester: string;
  risk_label: string;
}

export default function ExportPage() {
  const { user } = useAuthStore();
  const [options, setOptions] = useState<ExportOptions>({ semester: "", risk_label: "" });
  const [downloading, setDownloading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastExport, setLastExport] = useState<string | null>(null);

  const handleExport = async () => {
    setDownloading(true);
    setError(null);
    setSuccess(false);
    try {
      const params = new URLSearchParams();
      if (options.semester)   params.set("semester",   options.semester);
      if (options.risk_label) params.set("risk_label", options.risk_label);

      const response = await api.get(`/export/student-data?${params.toString()}`, {
        responseType: "blob",
      });

      // Trigger browser download
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
      const link = document.createElement("a");
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      link.href = url;
      link.download = `student_performance_${timestamp}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setSuccess(true);
      setLastExport(new Date().toLocaleString());
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: unknown) {
      const e = err as { response?: { status?: number } };
      if (e?.response?.status === 404 || e?.response?.status === 422) {
        setError("No data found for the selected filters.");
      } else {
        setError("Export failed — backend may be offline. Check that the server is running.");
      }
    } finally {
      setDownloading(false);
    }
  };

  const SEMESTERS = ["", "2024-EVEN", "2024-ODD", "2025-EVEN", "2025-ODD", "2026-EVEN"];

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100">
          <Download className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Export Student Data</h1>
          <p className="text-sm text-gray-500">
            {user?.role === "FACULTY"
              ? "Download performance data for your enrolled students"
              : "Download full cohort performance data as CSV"}
          </p>
        </div>
      </div>

      {/* Filter card */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-5">
          <Filter className="h-4 w-4 text-gray-400" />
          <h2 className="font-semibold text-gray-900">Export Filters</h2>
          <span className="text-xs text-gray-400 ml-1">(optional — leave blank to export all)</span>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Semester</label>
            <select
              className="input"
              value={options.semester}
              onChange={(e) => setOptions((o) => ({ ...o, semester: e.target.value }))}
            >
              <option value="">All semesters</option>
              {SEMESTERS.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Risk Level</label>
            <select
              className="input"
              value={options.risk_label}
              onChange={(e) => setOptions((o) => ({ ...o, risk_label: e.target.value }))}
            >
              <option value="">All risk levels</option>
              <option value="HIGH">High risk only</option>
              <option value="MEDIUM">Medium risk only</option>
              <option value="LOW">Low risk only</option>
            </select>
          </div>
        </div>

        {/* CSV columns preview */}
        <div className="rounded-xl bg-gray-50 p-4 mb-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2 flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" /> CSV Columns Included
          </p>
          <div className="flex flex-wrap gap-1.5">
            {[
              "student_id", "roll_no", "full_name", "email",
              "department", "semester", "batch_year",
              "risk_label", "risk_score", "attendance_pct",
              "assignment_avg", "predicted_at",
            ].map((col) => (
              <span key={col} className="rounded-lg bg-white border border-gray-200 px-2 py-0.5 text-xs font-mono text-gray-600">
                {col}
              </span>
            ))}
          </div>
        </div>

        <button
          onClick={handleExport}
          disabled={downloading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base"
        >
          <Download className="h-4 w-4" />
          {downloading ? "Preparing download…" : "Export Student Data (.csv)"}
        </button>
      </div>

      {/* Success */}
      {success && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 animate-fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
          <p className="text-sm font-medium text-emerald-700">File downloaded successfully!</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Last export */}
      {lastExport && (
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Clock className="h-3.5 w-3.5" />
          Last exported: {lastExport}
        </div>
      )}

      {/* Info box */}
      <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
        <p className="text-sm font-semibold text-blue-800 mb-1">About this export</p>
        <ul className="space-y-1 text-sm text-blue-700">
          <li>• Data is scoped to your enrolled students (faculty role)</li>
          <li>• Risk scores reflect the latest ML prediction run</li>
          <li>• Attendance and assignment figures are semester averages</li>
          <li>• Use in Excel or Google Sheets for further analysis</li>
        </ul>
      </div>
    </div>
  );
}
