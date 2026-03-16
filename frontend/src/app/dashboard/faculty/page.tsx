"use client";

// ─────────────────────────────────────────────────────────────────────────────
//  Faculty Dashboard — Overview · At Risk · All Students
// ─────────────────────────────────────────────────────────────────────────────
import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Users, AlertTriangle, BarChart2, ChevronRight,
  BookOpen, Activity, Search, Mail, CheckCircle,
} from "lucide-react";
import api from "@/lib/api";
import {
  PieChart, Pie, Cell, Tooltip as RTooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import RiskBadge from "@/components/dashboard/RiskBadge";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { useFacultyDashboard, useStudentsSummary } from "@/hooks/useFacultyDashboard";
import { usePredictions } from "@/hooks/usePredictions";
import { formatDate } from "@/lib/utils";
import type { RiskLabel } from "@/types";

// ── Types ─────────────────────────────────────────────────────────────────────
type Tab = "overview" | "at-risk" | "all";
type RiskFilter = "ALL" | RiskLabel;

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmt(n: number | null | undefined, suffix = "%") {
  if (n == null) return "—";
  return `${n.toFixed(1)}${suffix}`;
}

function RiskScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 60 ? "bg-red-500" : pct >= 35 ? "bg-amber-400" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-9 text-right text-xs font-medium tabular-nums text-gray-600">{pct}%</span>
    </div>
  );
}

function PctBar({ value, color = "bg-indigo-500" }: { value: number; color?: string }) {
  const pct = Math.min(100, Math.max(0, value));
  const textColor = pct < 60 ? "text-red-600" : pct < 75 ? "text-amber-600" : "text-emerald-600";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`w-10 text-right text-xs font-semibold tabular-nums ${textColor}`}>{pct.toFixed(0)}%</span>
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({
  title, value, sub, icon: Icon, iconBg, iconColor,
}: {
  title: string; value: string; sub?: string;
  icon: React.ElementType; iconBg: string; iconColor: string;
}) {
  return (
    <div className="card flex items-start gap-4 p-5">
      <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${iconBg}`}>
        <Icon className={`h-5 w-5 ${iconColor}`} />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{title}</p>
        <p className="mt-0.5 text-2xl font-bold text-gray-900">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-gray-500">{sub}</p>}
      </div>
    </div>
  );
}

// ── Pie colours ───────────────────────────────────────────────────────────────
const PIE_COLORS: Record<string, string> = {
  HIGH: "#ef4444", MEDIUM: "#f59e0b", LOW: "#22c55e",
};

// ── Main component ────────────────────────────────────────────────────────────
export default function FacultyDashboardPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("ALL");
  const [search, setSearch] = useState("");
  const [allPage, setAllPage] = useState(1);
  const [emailSending, setEmailSending] = useState(false);
  const [emailResult, setEmailResult] = useState<{ sent: number; attempted: number } | null>(null);

  // Dashboard summary (KPIs + charts)
  const { data: dash, loading: dashLoading } = useFacultyDashboard();

  // At-risk tab
  const { data: atRiskData, loading: atRiskLoading } = usePredictions({
    risk_label: riskFilter === "ALL" ? undefined : riskFilter,
    size: 100,
  });

  // All students tab (with metrics)
  const { data: allStudents, loading: allLoading } = useStudentsSummary({
    search: search.trim() || undefined,
    page: allPage,
    size: 50,
  });

  // Pie data
  const pieData = useMemo(() => {
    if (!dash) return [];
    const d = dash.risk_distribution;
    return [
      { name: "High", value: d.HIGH,   key: "HIGH"   },
      { name: "Medium", value: d.MEDIUM, key: "MEDIUM" },
      { name: "Low",  value: d.LOW,    key: "LOW"    },
    ].filter((x) => x.value > 0);
  }, [dash]);

  // Subject bar data
  const subjectData = dash?.subject_performance ?? [];

  const riskFilters: RiskFilter[] = ["ALL", "HIGH", "MEDIUM", "LOW"];

  async function sendRiskEmails() {
    const label = riskFilter === "ALL" ? "HIGH" : riskFilter;
    setEmailSending(true);
    setEmailResult(null);
    try {
      const { data } = await api.post("/alerts/send-emails", { risk_label: label });
      setEmailResult({ sent: data.sent, attempted: data.attempted });
    } catch {
      setEmailResult({ sent: 0, attempted: 0 });
    } finally {
      setEmailSending(false);
    }
  }

  // ── Tab button helper ──
  function TabBtn({ id, label, count }: { id: Tab; label: string; count?: number }) {
    return (
      <button
        onClick={() => setTab(id)}
        className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
          tab === id ? "bg-white text-indigo-700 shadow-sm" : "text-gray-600 hover:text-gray-900"
        }`}
      >
        {label}
        {count != null && (
          <span className={`rounded-full px-1.5 py-0.5 text-xs font-semibold ${
            tab === id ? "bg-indigo-100 text-indigo-700" : "bg-gray-200 text-gray-600"
          }`}>
            {count}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Faculty Dashboard</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Monitor your students' performance, attendance, and risk levels.
          </p>
        </div>
        {/* Quick search (all tab) */}
        {tab !== "overview" && (
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setAllPage(1); }}
              placeholder="Search students…"
              className="input pl-9"
            />
          </div>
        )}
      </div>

      {/* KPI Cards — always visible */}
      {dashLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-24 animate-pulse bg-gray-50 p-5" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard
            title="Total Students" icon={Users}
            value={(dash?.stats.total_students ?? 0).toString()}
            iconBg="bg-indigo-50" iconColor="text-indigo-600"
          />
          <KpiCard
            title="At Risk" icon={AlertTriangle}
            value={(dash?.stats.at_risk_count ?? 0).toString()}
            sub={dash ? `${((dash.stats.at_risk_count / Math.max(dash.stats.total_students, 1)) * 100).toFixed(0)}% of students` : undefined}
            iconBg="bg-red-50" iconColor="text-red-500"
          />
          <KpiCard
            title="Avg Attendance" icon={Activity}
            value={fmt(dash?.stats.avg_attendance_pct)}
            sub={dash && dash.stats.avg_attendance_pct < 75 ? "Below 75% threshold" : "On track"}
            iconBg="bg-violet-50" iconColor="text-violet-600"
          />
          <KpiCard
            title="Avg Assignment Score" icon={BookOpen}
            value={fmt(dash?.stats.avg_assignment_score)}
            iconBg="bg-emerald-50" iconColor="text-emerald-600"
          />
        </div>
      )}

      {/* Tab bar */}
      <div className="flex rounded-xl bg-gray-100 p-1 w-fit">
        <TabBtn id="overview"  label="Overview" />
        <TabBtn id="at-risk"   label="At Risk"      count={atRiskData?.total} />
        <TabBtn id="all"       label="All Students" count={allStudents?.total} />
      </div>

      {/* ── OVERVIEW TAB ─────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="space-y-6">
          {dashLoading ? <PageLoading /> : (
            <>
              {/* Charts row */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

                {/* Risk distribution pie */}
                <div className="card p-6">
                  <h2 className="mb-4 text-base font-semibold text-gray-800">Risk Distribution</h2>
                  {pieData.length === 0 ? (
                    <p className="py-8 text-center text-sm text-gray-400">No prediction data yet</p>
                  ) : (
                    <div className="flex items-center gap-6">
                      <ResponsiveContainer width={160} height={160}>
                        <PieChart>
                          <Pie data={pieData} dataKey="value" cx="50%" cy="50%"
                               innerRadius={45} outerRadius={75} paddingAngle={3}>
                            {pieData.map((entry) => (
                              <Cell key={entry.key} fill={PIE_COLORS[entry.key]} />
                            ))}
                          </Pie>
                          <RTooltip formatter={(v: number, n: string) => [v, n]} />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="flex flex-col gap-2">
                        {pieData.map((d) => (
                          <div key={d.key} className="flex items-center gap-2 text-sm">
                            <span className="h-3 w-3 rounded-full" style={{ background: PIE_COLORS[d.key] }} />
                            <span className="text-gray-600">{d.name}</span>
                            <span className="ml-auto font-semibold text-gray-900">{d.value}</span>
                          </div>
                        ))}
                        <div className="mt-1 border-t border-gray-100 pt-1 text-xs text-gray-400">
                          Total: {dash?.stats.total_students ?? 0} students
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Subject performance bar */}
                <div className="card p-6">
                  <h2 className="mb-4 text-base font-semibold text-gray-800">Subject Performance</h2>
                  {subjectData.length === 0 ? (
                    <p className="py-8 text-center text-sm text-gray-400">No subject data yet</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={subjectData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                        <XAxis dataKey="course_name" tick={{ fontSize: 11, fill: "#6b7280" }}
                               axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false}
                               tickLine={false} domain={[0, 100]} />
                        <RTooltip
                          contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}
                          formatter={(v: number, n: string) => [`${v.toFixed(1)}%`, n]}
                        />
                        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                        <Bar dataKey="avg_attendance_pct" name="Attendance" fill="#818cf8" radius={[4,4,0,0]} />
                        <Bar dataKey="avg_marks_pct"      name="Marks"      fill="#34d399" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              {/* Subject details table */}
              {subjectData.length > 0 && (
                <div className="card overflow-hidden">
                  <div className="border-b border-gray-100 px-6 py-4">
                    <h2 className="text-base font-semibold text-gray-800">Subject Summary</h2>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-100 text-sm">
                      <thead>
                        <tr className="table-header">
                          <th className="px-6 py-3 text-left">Subject</th>
                          <th className="px-6 py-3 text-right">Students</th>
                          <th className="px-6 py-3 text-right">Avg Attendance</th>
                          <th className="px-6 py-3 text-right">Avg Marks</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {subjectData.map((s) => (
                          <tr key={s.course_id} className="hover:bg-gray-50/60">
                            <td className="px-6 py-3 font-medium text-gray-900">{s.course_name}</td>
                            <td className="px-6 py-3 text-right tabular-nums text-gray-600">{s.student_count}</td>
                            <td className="px-6 py-3 text-right">
                              <PctBar value={s.avg_attendance_pct} color={s.avg_attendance_pct < 75 ? "bg-red-400" : "bg-indigo-400"} />
                            </td>
                            <td className="px-6 py-3 text-right">
                              <PctBar value={s.avg_marks_pct} color={s.avg_marks_pct < 50 ? "bg-red-400" : "bg-emerald-400"} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Top at-risk students preview */}
              {(atRiskData?.items.length ?? 0) > 0 && (
                <div className="card overflow-hidden">
                  <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
                    <h2 className="text-base font-semibold text-gray-800">Top At-Risk Students</h2>
                    <button onClick={() => setTab("at-risk")}
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-800">
                      View all →
                    </button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-100 text-sm">
                      <thead>
                        <tr className="table-header">
                          <th className="px-6 py-3 text-left">Student</th>
                          <th className="px-6 py-3 text-left">Risk Score</th>
                          <th className="px-6 py-3 text-left">Risk Level</th>
                          <th className="px-6 py-3 text-left">Top Factor</th>
                          <th className="px-6 py-3 text-left"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {atRiskData!.items.slice(0, 5).map((p) => (
                          <tr key={p.student_id} className="hover:bg-gray-50/60">
                            <td className="px-6 py-3">
                              <div className="flex items-center gap-3">
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100 text-xs font-bold text-red-700">
                                  {(p.student_name ?? "?").charAt(0).toUpperCase()}
                                </div>
                                <span className="font-medium text-gray-900">{p.student_name}</span>
                              </div>
                            </td>
                            <td className="px-6 py-3"><RiskScoreBar score={p.risk_score} /></td>
                            <td className="px-6 py-3"><RiskBadge label={p.risk_label} /></td>
                            <td className="px-6 py-3 text-gray-500 text-xs">
                              {p.contributing_factors[0]?.feature ?? "—"}
                            </td>
                            <td className="px-6 py-3">
                              <Link href={`/dashboard/analytics/${p.student_id}`}
                                className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800">
                                View <ChevronRight className="h-3 w-3" />
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── AT-RISK TAB ──────────────────────────────────────────────────── */}
      {tab === "at-risk" && (
        <>
          {/* Risk filter pills + Send Emails button */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {riskFilters.map((f) => (
                <button key={f} onClick={() => { setRiskFilter(f); setEmailResult(null); }}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    riskFilter === f
                      ? f === "HIGH" ? "bg-red-600 text-white"
                        : f === "MEDIUM" ? "bg-amber-500 text-white"
                        : f === "LOW" ? "bg-green-600 text-white"
                        : "bg-gray-700 text-white"
                      : f === "HIGH" ? "bg-red-50 text-red-700 ring-1 ring-red-200"
                        : f === "MEDIUM" ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                        : f === "LOW" ? "bg-green-50 text-green-700 ring-1 ring-green-200"
                        : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {f === "ALL" ? "All Levels" : f.charAt(0) + f.slice(1).toLowerCase()}
                </button>
              ))}
            </div>

            {/* Send email alerts button */}
            <div className="flex items-center gap-3">
              {emailResult && (
                <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
                  <CheckCircle className="h-4 w-4" />
                  {emailResult.sent}/{emailResult.attempted} emails sent
                </span>
              )}
              <button
                onClick={sendRiskEmails}
                disabled={emailSending || (atRiskData?.items.length ?? 0) === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Mail className="h-3.5 w-3.5" />
                {emailSending
                  ? "Sending…"
                  : `Send Alerts (${riskFilter === "ALL" ? "HIGH" : riskFilter})`}
              </button>
            </div>
          </div>

          {atRiskLoading ? (
            <PageLoading />
          ) : (atRiskData?.items.length ?? 0) === 0 ? (
            <EmptyState icon={AlertTriangle} title="No at-risk students"
              description={riskFilter !== "ALL"
                ? `No ${riskFilter.toLowerCase()} risk students found.`
                : "All students appear to be on track."} />
          ) : (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100 text-sm">
                  <thead>
                    <tr className="table-header">
                      <th className="px-6 py-3 text-left">Student</th>
                      <th className="px-6 py-3 text-left">Risk Score</th>
                      <th className="px-6 py-3 text-left">Risk Level</th>
                      <th className="px-6 py-3 text-left">Top Factor</th>
                      <th className="px-6 py-3 text-left">Predicted</th>
                      <th className="px-6 py-3 text-left"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {atRiskData!.items.map((p) => (
                      <tr key={p.student_id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
                              {(p.student_name ?? "?").charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium text-gray-900">{p.student_name}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4"><RiskScoreBar score={p.risk_score} /></td>
                        <td className="px-6 py-4"><RiskBadge label={p.risk_label} /></td>
                        <td className="px-6 py-4 text-gray-500">{p.contributing_factors[0]?.feature ?? "—"}</td>
                        <td className="px-6 py-4 text-gray-400 text-xs">{formatDate(p.predicted_at)}</td>
                        <td className="px-6 py-4">
                          <Link href={`/dashboard/analytics/${p.student_id}`}
                            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800">
                            View <ChevronRight className="h-3 w-3" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── ALL STUDENTS TAB ─────────────────────────────────────────────── */}
      {tab === "all" && (
        <>
          {allLoading ? (
            <PageLoading />
          ) : (allStudents?.items.length ?? 0) === 0 ? (
            <EmptyState icon={Users} title="No students found"
              description={search ? `No results for "${search}".` : "No students are assigned to your courses yet."} />
          ) : (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100 text-sm">
                  <thead>
                    <tr className="table-header">
                      <th className="px-6 py-3 text-left">Student</th>
                      <th className="px-6 py-3 text-left">Dept / Sem</th>
                      <th className="px-6 py-3 text-right">Attendance</th>
                      <th className="px-6 py-3 text-right">Marks</th>
                      <th className="px-6 py-3 text-right">Assignments</th>
                      <th className="px-6 py-3 text-left">Risk</th>
                      <th className="px-6 py-3 text-left"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {allStudents!.items.map((s) => (
                      <tr key={s.id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="px-6 py-3">
                          <div className="flex items-center gap-3">
                            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
                              {(s.full_name ?? "?").charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-medium text-gray-900">{s.full_name}</div>
                              <div className="font-mono text-xs text-gray-400">{s.roll_no}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-3 text-gray-500">
                          {s.department}<br />
                          <span className="text-xs">Sem {s.semester}</span>
                        </td>
                        <td className="px-6 py-3 text-right">
                          <PctBar value={s.attendance_pct} color={s.attendance_pct < 75 ? "bg-red-400" : "bg-indigo-400"} />
                        </td>
                        <td className="px-6 py-3 text-right">
                          <PctBar value={s.marks_pct} color={s.marks_pct < 50 ? "bg-red-400" : "bg-emerald-400"} />
                        </td>
                        <td className="px-6 py-3 text-right">
                          <PctBar value={s.assignment_pct} color={s.assignment_pct < 60 ? "bg-amber-400" : "bg-sky-400"} />
                        </td>
                        <td className="px-6 py-3">
                          {s.risk_label ? <RiskBadge label={s.risk_label as RiskLabel} /> : <span className="text-xs text-gray-400">—</span>}
                        </td>
                        <td className="px-6 py-3">
                          <Link href={`/dashboard/analytics/${s.id}`}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors">
                            <BarChart2 className="h-3.5 w-3.5" />
                            Analytics
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {(allStudents?.pages ?? 0) > 1 && (
                <div className="flex items-center justify-between border-t border-gray-100 px-6 py-3">
                  <span className="text-xs text-gray-400">
                    Page {allPage} of {allStudents!.pages} · {allStudents!.total} students
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => setAllPage((p) => Math.max(1, p - 1))}
                      disabled={allPage <= 1}
                      className="rounded-lg border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40">
                      Prev
                    </button>
                    <button onClick={() => setAllPage((p) => Math.min(allStudents!.pages, p + 1))}
                      disabled={allPage >= allStudents!.pages}
                      className="rounded-lg border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40">
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

    </div>
  );
}
