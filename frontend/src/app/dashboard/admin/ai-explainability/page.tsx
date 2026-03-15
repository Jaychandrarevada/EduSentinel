"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import {
  Sparkles, RefreshCw, AlertCircle, Info, ChevronRight,
  TrendingUp, TrendingDown, Search, User,
} from "lucide-react";
import api from "@/lib/api";
import { GlobalShapResult, StudentShapResult, FeatureImportance } from "@/types";

// ── Pretty feature labels ──────────────────────────────────────────────────
const FEATURE_LABELS: Record<string, string> = {
  attendance_pct:               "Attendance %",
  ia1_score:                    "IA-1 Score",
  ia2_score:                    "IA-2 Score",
  ia3_score:                    "IA-3 Score",
  assignment_avg_score:         "Assignment Avg",
  assignment_completion_rate:   "Assignment Completion",
  lms_engagement_score:         "LMS Engagement",
  lms_logins_per_week:          "LMS Logins / Week",
  forum_posts_per_week:         "Forum Activity",
  previous_gpa:                 "Previous GPA",
  content_views_per_week:       "Content Views / Week",
};

function label(f: string) { return FEATURE_LABELS[f] ?? f.replace(/_/g, " "); }

const DEMO_GLOBAL: GlobalShapResult = {
  feature_importance: [
    { feature: "attendance_pct",             importance: 0.28, description: "Attendance percentage" },
    { feature: "ia1_score",                  importance: 0.19, description: "Internal Assessment 1" },
    { feature: "assignment_avg_score",       importance: 0.15, description: "Assignment average" },
    { feature: "ia2_score",                  importance: 0.14, description: "Internal Assessment 2" },
    { feature: "lms_engagement_score",       importance: 0.12, description: "LMS engagement" },
    { feature: "previous_gpa",               importance: 0.08, description: "Previous GPA" },
    { feature: "assignment_completion_rate", importance: 0.04, description: "Assignment completion" },
  ],
  model_name: "XGBoost",
  data_source: "demo",
};

const DEMO_STUDENT: StudentShapResult = {
  student_id: 1,
  risk_score: 0.73,
  risk_label: "HIGH",
  explanation: [
    { feature: "attendance_pct",             value: 58.0,  shap_value:  0.31, direction: "increases_risk" },
    { feature: "ia1_score",                  value: 44.0,  shap_value:  0.22, direction: "increases_risk" },
    { feature: "lms_engagement_score",       value: 35.0,  shap_value:  0.18, direction: "increases_risk" },
    { feature: "assignment_avg_score",       value: 52.0,  shap_value:  0.14, direction: "increases_risk" },
    { feature: "previous_gpa",               value: 7.2,   shap_value: -0.12, direction: "decreases_risk" },
    { feature: "ia2_score",                  value: 55.0,  shap_value:  0.09, direction: "increases_risk" },
    { feature: "assignment_completion_rate", value: 65.0,  shap_value: -0.05, direction: "decreases_risk" },
  ],
};

function RiskBadge({ label }: { label: string }) {
  const cls = label === "HIGH"
    ? "bg-red-100 text-red-700 border-red-200"
    : label === "MEDIUM"
    ? "bg-amber-100 text-amber-700 border-amber-200"
    : "bg-green-100 text-green-700 border-green-200";
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${cls}`}>{label}</span>;
}

export default function AIExplainabilityPage() {
  const [globalData, setGlobalData]   = useState<GlobalShapResult | null>(null);
  const [studentData, setStudentData] = useState<StudentShapResult | null>(null);
  const [studentId, setStudentId]     = useState<string>("");
  const [loading, setLoading]         = useState(true);
  const [searching, setSearching]     = useState(false);
  const [error, setError]             = useState<string | null>(null);
  const [studentError, setStudentError] = useState<string | null>(null);

  const fetchGlobal = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<GlobalShapResult>("/ml/shap/global");
      setGlobalData(data);
    } catch {
      setGlobalData(DEMO_GLOBAL);
      setError("ML service offline — showing demo feature importance.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchGlobal(); }, [fetchGlobal]);

  const handleStudentSearch = async () => {
    if (!studentId.trim()) return;
    setSearching(true);
    setStudentError(null);
    try {
      const { data } = await api.post<StudentShapResult>("/ml/shap/student", { student_id: parseInt(studentId) });
      setStudentData(data);
    } catch {
      setStudentData({ ...DEMO_STUDENT, student_id: parseInt(studentId) || 1 });
      setStudentError("Using demo explanation — student not found in prediction store.");
    } finally {
      setSearching(false);
    }
  };

  const g = globalData ?? DEMO_GLOBAL;
  const sorted = [...g.feature_importance].sort((a, b) => b.importance - a.importance);
  const maxImp = sorted[0]?.importance ?? 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
            <Sparkles className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">AI Explainability (SHAP)</h1>
            <p className="text-sm text-gray-500">Understand why the model predicts each student as at-risk</p>
          </div>
        </div>
        <button
          onClick={fetchGlobal}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-500" />
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {/* SHAP explainer intro */}
      <div className="flex items-start gap-3 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3">
        <Info className="h-4 w-4 shrink-0 mt-0.5 text-indigo-500" />
        <p className="text-sm text-indigo-700">
          <span className="font-semibold">SHAP (SHapley Additive exPlanations)</span> attributes the model's prediction to each input feature.
          Positive SHAP values push the prediction toward HIGH risk; negative values pull toward LOW risk.
          Model: <span className="font-semibold">{g.model_name}</span>
          {g.data_source === "demo" && <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">Demo</span>}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Global feature importance — bar chart */}
        <div className="card p-6 col-span-1">
          <div className="flex items-center gap-2 mb-5">
            <TrendingUp className="h-4 w-4 text-indigo-500" />
            <h2 className="font-semibold text-gray-900">Global Feature Importance</h2>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={sorted.map((f) => ({ name: label(f.feature), value: +(f.importance * 100).toFixed(1) }))}
              layout="vertical"
              margin={{ top: 0, right: 20, bottom: 0, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
              <XAxis type="number" unit="%" tick={{ fontSize: 11, fill: "#9ca3af" }} domain={[0, 35]} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#374151" }} width={140} />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={{ borderRadius: "12px", border: "1px solid #e5e7eb" }} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={18}>
                {sorted.map((f, i) => (
                  <Cell key={i} fill={`hsl(${240 - i * 22}, 70%, ${55 + i * 4}%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Importance visual list */}
        <div className="card p-6 col-span-1">
          <div className="flex items-center gap-2 mb-5">
            <ChevronRight className="h-4 w-4 text-gray-400" />
            <h2 className="font-semibold text-gray-900">Feature Impact Breakdown</h2>
          </div>
          <div className="space-y-3">
            {sorted.map((f, i) => (
              <div key={f.feature}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-700 font-medium">{label(f.feature)}</span>
                  <span className="text-xs font-semibold tabular-nums text-gray-500">{(f.importance * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${(f.importance / maxImp) * 100}%`,
                      backgroundColor: `hsl(${240 - i * 22}, 70%, ${55 + i * 4}%)`,
                    }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-0.5">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Individual student explanation */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-5">
          <User className="h-4 w-4 text-gray-500" />
          <h2 className="font-semibold text-gray-900">Individual Student Explanation</h2>
        </div>

        {/* Search bar */}
        <div className="flex gap-3 mb-6">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="number"
              placeholder="Enter Student ID"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStudentSearch()}
              className="input pl-9"
            />
          </div>
          <button
            onClick={handleStudentSearch}
            disabled={searching || !studentId.trim()}
            className="btn-primary flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            {searching ? "Explaining…" : "Explain"}
          </button>
          <button
            onClick={() => { setStudentId("1"); setTimeout(handleStudentSearch, 0); setStudentData(DEMO_STUDENT); }}
            className="btn-secondary text-xs"
          >
            Load Demo (ID 1)
          </button>
        </div>

        {studentError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
            <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
            <p className="text-xs text-amber-700">{studentError}</p>
          </div>
        )}

        {studentData && (
          <div className="space-y-4">
            {/* Risk summary */}
            <div className="flex items-center gap-4 rounded-xl bg-gray-50 px-5 py-4">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Student ID</p>
                <p className="text-lg font-bold text-gray-900">#{studentData.student_id}</p>
              </div>
              <div className="h-8 w-px bg-gray-200" />
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Risk Label</p>
                <RiskBadge label={studentData.risk_label} />
              </div>
              <div className="h-8 w-px bg-gray-200" />
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Risk Score</p>
                <p className="text-lg font-bold text-red-600">{(studentData.risk_score * 100).toFixed(0)}%</p>
              </div>
              {/* Mini force-plot bar */}
              <div className="flex-1 ml-4">
                <p className="text-xs text-gray-400 mb-1">Risk Probability</p>
                <div className="h-3 w-full rounded-full bg-gray-200 overflow-hidden">
                  <div
                    className="h-3 rounded-full"
                    style={{
                      width: `${studentData.risk_score * 100}%`,
                      background: studentData.risk_score > 0.7
                        ? "linear-gradient(90deg, #f59e0b, #ef4444)"
                        : studentData.risk_score > 0.4
                        ? "linear-gradient(90deg, #10b981, #f59e0b)"
                        : "linear-gradient(90deg, #6366f1, #10b981)",
                    }}
                  />
                </div>
              </div>
            </div>

            {/* SHAP waterfall */}
            <div>
              <p className="mb-3 text-sm font-medium text-gray-600">Feature contributions to this prediction:</p>
              <div className="space-y-2">
                {studentData.explanation
                  .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
                  .map((e, i) => {
                    const isRisk = e.direction === "increases_risk";
                    const maxVal = Math.max(...studentData.explanation.map(x => Math.abs(x.shap_value)));
                    const barPct = (Math.abs(e.shap_value) / maxVal) * 100;
                    return (
                      <div key={i} className="flex items-center gap-3 rounded-xl bg-gray-50 px-4 py-3">
                        <div className="w-40 shrink-0">
                          <p className="text-sm font-medium text-gray-800 truncate">{label(e.feature)}</p>
                          <p className="text-xs text-gray-400">Value: {e.value.toFixed(1)}</p>
                        </div>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-2 rounded-full ${isRisk ? "bg-red-400" : "bg-emerald-400"}`}
                            style={{ width: `${barPct}%` }}
                          />
                        </div>
                        <div className="flex items-center gap-1.5 w-28 justify-end">
                          {isRisk
                            ? <TrendingUp className="h-3.5 w-3.5 text-red-500" />
                            : <TrendingDown className="h-3.5 w-3.5 text-emerald-500" />
                          }
                          <span className={`text-xs font-bold tabular-nums ${isRisk ? "text-red-600" : "text-emerald-600"}`}>
                            {isRisk ? "+" : ""}{e.shap_value.toFixed(3)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Suggestions */}
            <div className="rounded-xl border border-blue-100 bg-blue-50 px-5 py-4">
              <p className="text-sm font-semibold text-blue-800 mb-2">Improvement Suggestions</p>
              <ul className="space-y-1.5">
                {studentData.explanation.filter(e => e.direction === "increases_risk").slice(0, 3).map((e) => {
                  const suggestions: Record<string, string> = {
                    attendance_pct: "Attend at least 75% of all classes to meet the minimum threshold",
                    ia1_score: "Revise IA-1 topics and seek tutoring for weak areas",
                    ia2_score: "Focus on IA-2 syllabus; practice previous year questions",
                    lms_engagement_score: "Spend at least 2 hours/day on LMS and complete pending modules",
                    assignment_avg_score: "Submit all pending assignments; aim for >70% average",
                    assignment_completion_rate: "Ensure 100% assignment submission rate",
                  };
                  return (
                    <li key={e.feature} className="flex items-start gap-2 text-sm text-blue-700">
                      <span className="text-blue-400 mt-0.5">•</span>
                      {suggestions[e.feature] ?? `Improve ${label(e.feature)} (currently ${e.value.toFixed(1)})`}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}

        {!studentData && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Sparkles className="h-10 w-10 text-gray-200 mb-3" />
            <p className="text-sm text-gray-400">Enter a student ID above to see their SHAP explanation</p>
            <p className="text-xs text-gray-300 mt-1">or click "Load Demo" to see an example</p>
          </div>
        )}
      </div>
    </div>
  );
}
