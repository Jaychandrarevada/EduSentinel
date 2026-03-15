"use client";

// ─────────────────────────────────────────────
//  Admin → Analytics — Cohort & Department Deep-Dive
// ─────────────────────────────────────────────
import { useState } from "react";
import { useCohortOverview, useDepartmentStats } from "@/hooks/useAnalytics";
import { usePredictions } from "@/hooks/usePredictions";
import DepartmentRiskChart from "@/components/charts/DepartmentRiskChart";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import PerformanceTrendChart from "@/components/charts/PerformanceTrendChart";
import type { TrendDataPoint } from "@/components/charts/PerformanceTrendChart";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import { formatPct } from "@/lib/utils";
import {
  TrendingUp, TrendingDown, Users, AlertTriangle, Activity, BookOpen,
} from "lucide-react";

const TREND_DATA: TrendDataPoint[] = [
  { label: "Aug", attendance: 88, marks: 82, lms_engagement: 74 },
  { label: "Sep", attendance: 85, marks: 79, lms_engagement: 71 },
  { label: "Oct", attendance: 80, marks: 75, lms_engagement: 68 },
  { label: "Nov", attendance: 76, marks: 72, lms_engagement: 63 },
  { label: "Dec", attendance: 74, marks: 70, lms_engagement: 60 },
  { label: "Jan", attendance: 71, marks: 67, lms_engagement: 58 },
  { label: "Feb", attendance: 69, marks: 65, lms_engagement: 55 },
];

const SEMESTERS = ["All", "Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"];

interface KpiCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  trend?: "up" | "down" | "neutral";
  icon: React.ElementType;
  iconColor: string;
  bgColor: string;
}

function KpiCard({ title, value, subtext, trend, icon: Icon, iconColor, bgColor }: KpiCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${bgColor}`}>
          <Icon className={`h-5 w-5 ${iconColor}`} />
        </div>
        {trend && (
          <span className={`text-xs font-semibold ${trend === "up" ? "text-emerald-600" : trend === "down" ? "text-red-500" : "text-gray-400"}`}>
            {trend === "up" ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
          </span>
        )}
      </div>
      <p className="mt-3 text-2xl font-bold text-gray-900">{value}</p>
      <p className="mt-0.5 text-sm font-medium text-gray-600">{title}</p>
      {subtext && <p className="mt-1 text-xs text-gray-400">{subtext}</p>}
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const [semester, setSemester] = useState("All");
  const semParam = semester === "All" ? undefined : semester;

  const { data: cohort, loading: cohortLoading } = useCohortOverview(semParam);
  const { data: deptStats, loading: deptLoading } = useDepartmentStats(semParam);
  const { data: predictions } = usePredictions({ size: 200 });

  if (cohortLoading || deptLoading) return <PageLoading />;

  const total = cohort?.total_students ?? 1240;
  const high = cohort?.high_risk_count ?? 87;
  const medium = cohort?.medium_risk_count ?? 193;
  const low = cohort?.low_risk_count ?? 960;
  const avgAtt = cohort?.avg_attendance_pct ?? 74.2;
  const avgMarks = cohort?.avg_marks_pct ?? 68.5;
  const alerts = cohort?.unresolved_alerts ?? 12;

  // Department table data
  const departments = deptStats && deptStats.length > 0 ? deptStats : [
    { department: "CSE",   total_students: 320, high_risk_count: 42, avg_attendance_pct: 78, avg_marks_pct: 71 },
    { department: "ECE",   total_students: 280, high_risk_count: 35, avg_attendance_pct: 75, avg_marks_pct: 68 },
    { department: "MECH",  total_students: 210, high_risk_count: 28, avg_attendance_pct: 72, avg_marks_pct: 65 },
    { department: "CIVIL", total_students: 190, high_risk_count: 20, avg_attendance_pct: 80, avg_marks_pct: 73 },
    { department: "IT",    total_students: 240, high_risk_count: 31, avg_attendance_pct: 76, avg_marks_pct: 69 },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-0.5 text-sm text-gray-500">Cohort performance overview and department breakdown</p>
        </div>
        <select
          value={semester}
          onChange={(e) => setSemester(e.target.value)}
          className="input w-36"
        >
          {SEMESTERS.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KpiCard title="Total Students" value={total.toLocaleString()} icon={Users} iconColor="text-indigo-600" bgColor="bg-indigo-50" />
        <KpiCard title="High Risk" value={high} subtext={`${formatPct(high / total * 100)} of cohort`} icon={AlertTriangle} iconColor="text-red-500" bgColor="bg-red-50" trend="down" />
        <KpiCard title="Medium Risk" value={medium} icon={AlertTriangle} iconColor="text-amber-500" bgColor="bg-amber-50" />
        <KpiCard title="Low Risk" value={low} icon={Users} iconColor="text-emerald-600" bgColor="bg-emerald-50" trend="up" />
        <KpiCard title="Avg Attendance" value={formatPct(avgAtt)} subtext={avgAtt >= 75 ? "Above threshold" : "Below threshold"} icon={Activity} iconColor="text-violet-600" bgColor="bg-violet-50" />
        <KpiCard title="Avg Marks" value={formatPct(avgMarks)} icon={BookOpen} iconColor="text-sky-600" bgColor="bg-sky-50" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card p-6 lg:col-span-2">
          <h2 className="mb-1 text-base font-semibold text-gray-800">Department Risk Distribution</h2>
          <p className="mb-4 text-xs text-gray-400">Total vs high-risk count per department</p>
          <DepartmentRiskChart data={departments} />
        </div>
        <div className="card p-6">
          <h2 className="mb-1 text-base font-semibold text-gray-800">Cohort Risk Split</h2>
          <p className="mb-4 text-xs text-gray-400">All students · current semester</p>
          <RiskDistributionChart high={high} medium={medium} low={low} />
        </div>
      </div>

      {/* Trend chart */}
      <div className="card p-6">
        <h2 className="mb-1 text-base font-semibold text-gray-800">Performance Trend</h2>
        <p className="mb-4 text-xs text-gray-400">Monthly cohort averages — Attendance / Marks / LMS Engagement</p>
        <PerformanceTrendChart data={TREND_DATA} attendanceThreshold={75} />
      </div>

      {/* Department table */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-800">Department Summary</h2>
          <span className="text-xs text-gray-400">{departments.length} departments</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100 text-sm">
            <thead>
              <tr className="table-header">
                <th className="px-6 py-3 text-left">Department</th>
                <th className="px-6 py-3 text-right">Students</th>
                <th className="px-6 py-3 text-right">High Risk</th>
                <th className="px-6 py-3 text-right">Risk %</th>
                <th className="px-6 py-3 text-right">Avg Attendance</th>
                <th className="px-6 py-3 text-right">Avg Marks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {departments.map((d) => {
                const riskPct = (d.total_students ?? 0) > 0 ? ((d.high_risk_count ?? 0) / d.total_students) * 100 : 0;
                return (
                  <tr key={d.department} className="hover:bg-gray-50/60">
                    <td className="px-6 py-3 font-medium text-gray-900">{d.department}</td>
                    <td className="px-6 py-3 text-right tabular-nums text-gray-600">{(d.total_students ?? 0).toLocaleString()}</td>
                    <td className="px-6 py-3 text-right tabular-nums text-red-600 font-medium">{d.high_risk_count ?? 0}</td>
                    <td className="px-6 py-3 text-right tabular-nums">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${riskPct >= 20 ? "bg-red-50 text-red-700" : riskPct >= 10 ? "bg-amber-50 text-amber-700" : "bg-green-50 text-green-700"}`}>
                        {formatPct(riskPct)}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-right tabular-nums text-gray-600">{formatPct(d.avg_attendance_pct ?? 0)}</td>
                    <td className="px-6 py-3 text-right tabular-nums text-gray-600">{formatPct(d.avg_marks_pct ?? 0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
