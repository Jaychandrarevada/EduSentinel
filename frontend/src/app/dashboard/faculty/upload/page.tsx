"use client";

// ─────────────────────────────────────────────
//  Faculty → Data Upload
//  Upload attendance, marks, assignments, LMS via CSV
// ─────────────────────────────────────────────
import { useState, useRef } from "react";
import { Upload, Download, CheckCircle, AlertCircle, FileSpreadsheet, X } from "lucide-react";
import api from "@/lib/api";

type UploadType = "attendance" | "marks" | "assignments" | "lms";

interface UploadConfig {
  label: string;
  endpoint: string;
  columns: string[];
  description: string;
  color: string;
}

const UPLOAD_CONFIGS: Record<UploadType, UploadConfig> = {
  attendance: {
    label: "Attendance",
    endpoint: "/attendance/bulk",
    columns: ["student_id", "date", "status (PRESENT/ABSENT/LATE)"],
    description: "Daily attendance records",
    color: "bg-indigo-50 text-indigo-600 ring-indigo-200",
  },
  marks: {
    label: "Internal Marks",
    endpoint: "/academic/bulk",
    columns: ["student_id", "course_id", "assessment_type", "score", "max_score", "exam_date"],
    description: "IA1, IA2, IA3 and final exam scores",
    color: "bg-emerald-50 text-emerald-600 ring-emerald-200",
  },
  assignments: {
    label: "Assignments",
    endpoint: "/assignments/bulk",
    columns: ["student_id", "course_id", "title", "score", "max_score", "is_submitted", "is_late", "due_date"],
    description: "Assignment submissions and scores",
    color: "bg-violet-50 text-violet-600 ring-violet-200",
  },
  lms: {
    label: "LMS Activity",
    endpoint: "/lms-activity/bulk",
    columns: ["student_id", "date", "login_count", "content_views", "time_spent_minutes", "forum_posts"],
    description: "LMS interaction logs",
    color: "bg-amber-50 text-amber-600 ring-amber-200",
  },
};

interface UploadResult {
  success: number;
  failed: number;
  errors: Array<{ row: number; error: string }>;
}

function UploadCard({ type, config }: { type: UploadType; config: UploadConfig }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File | null) => {
    if (!f) return;
    if (!f.name.endsWith(".csv") && !f.name.endsWith(".json")) {
      setError("Only CSV and JSON files are supported.");
      return;
    }
    setFile(f);
    setResult(null);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0] ?? null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setResult(null);
    setError(null);

    try {
      const text = await file.text();
      let records: unknown[];

      if (file.name.endsWith(".json")) {
        records = JSON.parse(text);
      } else {
        // Parse CSV
        const lines = text.trim().split("\n");
        const headers = lines[0].split(",").map((h) => h.trim());
        records = lines.slice(1).map((line) => {
          const vals = line.split(",").map((v) => v.trim());
          return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? ""]));
        });
      }

      const r = await api.post(config.endpoint, { records });
      setResult(r.data);
      setFile(null);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? "Upload failed. Check the file format.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ring-1 ${config.color}`}>
          <FileSpreadsheet className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{config.label}</h3>
          <p className="text-xs text-gray-500">{config.description}</p>
        </div>
      </div>

      {/* Expected columns */}
      <div className="mb-4">
        <p className="mb-1.5 text-xs font-medium text-gray-600">Expected columns:</p>
        <div className="flex flex-wrap gap-1">
          {config.columns.map((col) => (
            <code key={col} className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">{col}</code>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-colors ${dragging ? "border-indigo-400 bg-indigo-50" : "border-gray-200 bg-gray-50 hover:border-gray-300"}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.json"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div className="flex items-center gap-2 text-sm">
            <FileSpreadsheet className="h-4 w-4 text-indigo-600" />
            <span className="font-medium text-gray-900">{file.name}</span>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="mb-2 h-8 w-8 text-gray-300" />
            <p className="text-sm font-medium text-gray-600">Drop CSV / JSON here</p>
            <p className="mt-0.5 text-xs text-gray-400">or click to browse</p>
          </>
        )}
      </div>

      {/* Result / Error */}
      {result && (
        <div className={`mt-4 rounded-lg p-4 text-sm ${result.failed === 0 ? "bg-emerald-50 ring-1 ring-emerald-200" : "bg-amber-50 ring-1 ring-amber-200"}`}>
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle className={`h-4 w-4 ${result.failed === 0 ? "text-emerald-600" : "text-amber-500"}`} />
            {result.success} rows imported
            {result.failed > 0 && `, ${result.failed} failed`}
          </div>
          {result.errors.slice(0, 3).map((e, i) => (
            <p key={i} className="mt-1 text-xs text-gray-600">Row {e.row}: {e.error}</p>
          ))}
        </div>
      )}
      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="btn-primary flex flex-1 items-center justify-center gap-2 disabled:opacity-50"
        >
          {uploading ? (
            <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> Uploading…</>
          ) : (
            <><Upload className="h-4 w-4" /> Upload</>
          )}
        </button>
        <a
          href={`/sample_uploads/${type}_template.csv`}
          download
          className="btn-secondary flex items-center gap-1.5 text-xs"
          onClick={(e) => e.stopPropagation()}
        >
          <Download className="h-3.5 w-3.5" /> Template
        </a>
      </div>
    </div>
  );
}

export default function FacultyUploadPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Upload</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Import student data via CSV or JSON. Download templates to get the right format.
        </p>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <strong>Note:</strong> Uploaded records are upserted (existing data for the same student/date is updated, not duplicated).
        Maximum 500 records per upload.
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {(Object.entries(UPLOAD_CONFIGS) as [UploadType, UploadConfig][]).map(([type, config]) => (
          <UploadCard key={type} type={type} config={config} />
        ))}
      </div>
    </div>
  );
}
