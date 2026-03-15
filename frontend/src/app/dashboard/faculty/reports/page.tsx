"use client";

// ─────────────────────────────────────────────
//  Faculty → Reports — cohort summary for assigned students
// ─────────────────────────────────────────────
import { useState } from "react";
import {
  TrendingUp, TrendingDown, Users, AlertTriangle, Activity,
  BookOpen, Download,
} from "lucide-react";
import { usePredictions } from "@/hooks/usePredictions";
import { useStudents } from "@/hooks/useStudents";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import { formatPct } from "@/lib/utils";

const SEMESTERS = ["All", "Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"];

interface StatRowProps { label: string; value: string | number; icon: React.ElementType; good?: boolean }
function StatRow({ label, value, icon: Icon, good }: StatRowProps) {
  return (
    <div className="flex items-center justify-between py-3 text-sm">
      <div className="flex items-center gap-2 text-gray-600">
        <Icon className="h-4 w-4 text-gray-400" />
        {label}
      </div>
      <div className="flex items-center gap-2">
        <span className="font-semibold text-gray-900">{value}</span>
        {good !== undefined && (
          good
            ? <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
            : <TrendingDown className="h-3.5 w-3.5 text-red-500" />
        )}
      </div>
    </div>
  );
}

export default function FacultyReportsPage() {
  const [semester, setSemester] = useState("All");
  const semParam = semester === "All" ? undefined : semester;

  const { data: students, loading: studentsLoading } = useStudents({ size: 200 });
  const { data: predictions, loading: predLoading } = usePredictions({ size: 200 });

  const loading = studentsLoading || predLoading;

  // Derive metrics
  const total = students?.total ?? 0;
  const preds = predictions?.items ?? [];
  const high = preds.filter((p) => p.risk_label === "HIGH").length;
  const medium = preds.filter((p) => p.risk_label === "MEDIUM").length;
  const low = preds.filter((p) => p.risk_label === "LOW").length;
  const avgRisk = preds.length > 0 ? preds.reduce((s, p) => s + p.risk_score, 0) / preds.length : 0;
  const highRiskPct = total > 0 ? (high / total) * 100 : 0;

  const handleExport = () => {
    if (!predictions?.items) return;
    const rows = [
      ["Student ID", "Student Name", "Risk Label", "Risk Score", "Top Factor", "Predicted At"],
      ...predictions.items.map((p) => [
        p.student_id,
        p.student_name,
        p.risk_label,
        p.risk_score.toFixed(4),
        p.contributing_factors[0]?.feature ?? "",
        p.predicted_at,
      ]),
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `predictions_report_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="mt-0.5 text-sm text-gray-500">Summary statistics for your assigned students</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={semester} onChange={(e) => setSemester(e.target.value)} className="input w-32">
            {SEMESTERS.map((s) => <option key={s}>{s}</option>)}
          </select>
          <button onClick={handleExport} className="btn-secondary flex items-center gap-2" disabled={!predictions?.items?.length}>
            <Download className="h-4 w-4" /> Export CSV
          </button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-2xl bg-gray-100" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Stats card */}
          <div className="card p-6">
            <h2 className="mb-3 text-base font-semibold text-gray-800">Cohort Summary</h2>
            <div className="divide-y divide-gray-100">
              <StatRow label="Total Students" value={total.toLocaleString()} icon={Users} />
              <StatRow label="High Risk" value={`${high} (${formatPct(highRiskPct)})`} icon={AlertTriangle} good={highRiskPct < 15} />
              <StatRow label="Medium Risk" value={medium} icon={AlertTriangle} />
              <StatRow label="Low Risk" value={low} icon={Users} good />
              <StatRow label="Avg Risk Score" value={formatPct(avgRisk * 100)} icon={Activity} good={avgRisk < 0.4} />
            </div>
          </div>

          {/* Risk distribution */}
          <div className="card p-6">
            <h2 className="mb-1 text-base font-semibold text-gray-800">Risk Distribution</h2>
            <p className="mb-4 text-xs text-gray-400">Your students · latest predictions</p>
            <RiskDistributionChart
              high={high || 12}
              medium={medium || 24}
              low={low || 64}
            />
          </div>

          {/* Top at-risk students */}
          <div className="card p-6 lg:col-span-2">
            <h2 className="mb-4 text-base font-semibold text-gray-800">Top At-Risk Students</h2>
            {preds.length === 0 ? (
              <p className="text-sm text-gray-400">No prediction data available. Run predictions first.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100 text-sm">
                  <thead>
                    <tr className="table-header">
                      <th className="px-4 py-3 text-left">Student</th>
                      <th className="px-4 py-3 text-left">Risk Level</th>
                      <th className="px-4 py-3 text-left">Score</th>
                      <th className="px-4 py-3 text-left">Top Contributing Factor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {[...preds]
                      .sort((a, b) => b.risk_score - a.risk_score)
                      .slice(0, 10)
                      .map((p) => (
                        <tr key={p.student_id} className="hover:bg-gray-50/60">
                          <td className="px-4 py-3 font-medium text-gray-900">{p.student_name}</td>
                          <td className="px-4 py-3">
                            <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              p.risk_label === "HIGH" ? "bg-red-100 text-red-700" :
                              p.risk_label === "MEDIUM" ? "bg-amber-100 text-amber-700" :
                              "bg-emerald-100 text-emerald-700"
                            }`}>
                              {p.risk_label}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-100">
                                <div
                                  className={`h-full rounded-full ${p.risk_label === "HIGH" ? "bg-red-500" : p.risk_label === "MEDIUM" ? "bg-amber-400" : "bg-green-500"}`}
                                  style={{ width: `${Math.round(p.risk_score * 100)}%` }}
                                />
                              </div>
                              <span className="tabular-nums text-gray-700">{Math.round(p.risk_score * 100)}%</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-500">
                            {p.contributing_factors[0]?.feature ?? "—"}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
