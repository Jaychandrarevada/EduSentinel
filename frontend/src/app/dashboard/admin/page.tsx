"use client";

// ─────────────────────────────────────────────
//  Admin Dashboard – Overview
// ─────────────────────────────────────────────
import { useState } from "react";
import {
  Users,
  AlertTriangle,
  TrendingUp,
  Activity,
  RefreshCw,
} from "lucide-react";
import StatCard from "@/components/dashboard/StatCard";
import RiskBadge from "@/components/dashboard/RiskBadge";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import PerformanceTrendChart from "@/components/charts/PerformanceTrendChart";
import type { TrendDataPoint } from "@/components/charts/PerformanceTrendChart";
import DepartmentRiskChart from "@/components/charts/DepartmentRiskChart";
import type { DepartmentStat } from "@/hooks/useAnalytics";
import { useCohortOverview, useDepartmentStats, usePredictionSummary } from "@/hooks/useAnalytics";
import { usePredictions } from "@/hooks/usePredictions";
import { formatPct, formatDate } from "@/lib/utils";

// ── Static fallback data ──────────────────────

const TREND_DATA: TrendDataPoint[] = [
  { label: "Aug", attendance: 88, marks: 82, lms_engagement: 74 },
  { label: "Sep", attendance: 85, marks: 79, lms_engagement: 71 },
  { label: "Oct", attendance: 80, marks: 75, lms_engagement: 68 },
  { label: "Nov", attendance: 76, marks: 72, lms_engagement: 63 },
  { label: "Dec", attendance: 74, marks: 70, lms_engagement: 60 },
  { label: "Jan", attendance: 71, marks: 67, lms_engagement: 58 },
  { label: "Feb", attendance: 69, marks: 65, lms_engagement: 55 },
];

const DEPT_FALLBACK: DepartmentStat[] = [
  { department: "CSE",  total: 320, high_risk: 42, avg_attendance: 78, avg_marks: 71 },
  { department: "ECE",  total: 280, high_risk: 35, avg_attendance: 75, avg_marks: 68 },
  { department: "MECH", total: 210, high_risk: 28, avg_attendance: 72, avg_marks: 65 },
  { department: "CIVIL",total: 190, high_risk: 20, avg_attendance: 80, avg_marks: 73 },
  { department: "IT",   total: 240, high_risk: 31, avg_attendance: 76, avg_marks: 69 },
];

const FALLBACK_LIST = [
  {
    student_id: 1001,
    student_name: "Aarav Sharma",
    risk_label: "HIGH" as const,
    risk_score: 0.91,
    contributing_factors: [{ feature: "Low Attendance", impact: 0.42, value: 52 }],
    model_version: "v1",
    predicted_at: "2025-02-10T08:30:00Z",
  },
  {
    student_id: 1002,
    student_name: "Priya Nair",
    risk_label: "HIGH" as const,
    risk_score: 0.85,
    contributing_factors: [{ feature: "Missed Assignments", impact: 0.38, value: 3 }],
    model_version: "v1",
    predicted_at: "2025-02-10T08:30:00Z",
  },
  {
    student_id: 1003,
    student_name: "Rohan Mehta",
    risk_label: "HIGH" as const,
    risk_score: 0.79,
    contributing_factors: [{ feature: "Low LMS Engagement", impact: 0.31, value: 12 }],
    model_version: "v1",
    predicted_at: "2025-02-10T08:30:00Z",
  },
];

const SEMESTERS = ["All", "Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"];

// ── Component ─────────────────────────────────
export default function AdminDashboardPage() {
  const [semester, setSemester] = useState("All");

  const semParam = semester === "All" ? undefined : semester;

  const { data: cohort, loading: cohortLoading } = useCohortOverview(semParam);
  const { data: deptStats, loading: deptLoading } = useDepartmentStats(semParam);
  const { data: predSummary } = usePredictionSummary(semParam);
  const { data: atRiskData, loading: riskLoading } = usePredictions({
    risk_label: "HIGH",
    size: 5,
  });

  // Resolve live vs fallback values
  const total = cohort?.total_students ?? 1240;
  const highRisk = predSummary?.high_risk_count ?? cohort?.high_risk_count ?? 87;
  const mediumRisk = cohort?.medium_risk_count ?? 193;
  const lowRisk = cohort?.low_risk_count ?? 960;
  const avgAttendance = cohort?.avg_attendance_pct ?? 74.2;
  const avgMarks = cohort?.avg_marks_pct ?? 68.5;
  const highRiskPct = predSummary?.high_risk_pct ?? ((highRisk / total) * 100);

  const deptData: DepartmentStat[] =
    deptStats && deptStats.length > 0 ? deptStats : DEPT_FALLBACK;

  const flaggedStudents =
    atRiskData && atRiskData.items.length > 0 ? atRiskData.items : FALLBACK_LIST;

  const isLoading = cohortLoading || deptLoading || riskLoading;

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Real-time student performance monitoring
            {predSummary?.last_run_at && (
              <span className="ml-2 text-gray-400">
                · Last model run: {formatDate(predSummary.last_run_at)}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Semester selector */}
          <select
            value={semester}
            onChange={(e) => setSemester(e.target.value)}
            className="input w-36"
          >
            {SEMESTERS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <button
            className="btn-secondary flex items-center gap-2"
            onClick={() => window.location.reload()}
            title="Refresh data"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Students"
          value={total.toLocaleString()}
          icon={Users}
          iconColor="text-indigo-600"
        />
        <StatCard
          title="High Risk"
          value={highRisk}
          delta={`${formatPct(highRiskPct)} of total`}
          deltaPositive={false}
          icon={AlertTriangle}
          iconColor="text-red-500"
        />
        <StatCard
          title="Avg Attendance"
          value={formatPct(avgAttendance)}
          delta={avgAttendance >= 75 ? "Above threshold" : `${formatPct(75 - avgAttendance)} below threshold`}
          deltaPositive={avgAttendance >= 75}
          icon={Activity}
          iconColor="text-emerald-600"
        />
        <StatCard
          title="Avg Marks"
          value={formatPct(avgMarks)}
          delta={avgMarks >= 50 ? "Passing average" : "Below passing mark"}
          deltaPositive={avgMarks >= 50}
          icon={TrendingUp}
          iconColor="text-violet-600"
        />
      </div>

      {/* Row 1: Risk distribution + Performance trend */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Risk distribution donut */}
        <div className="card p-6">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            Risk Distribution
          </h2>
          <p className="mb-4 text-xs text-gray-400">Current semester cohort</p>
          <RiskDistributionChart
            high={highRisk}
            medium={mediumRisk}
            low={lowRisk}
          />
        </div>

        {/* Performance trend line chart */}
        <div className="card p-6">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            Performance Trend
          </h2>
          <p className="mb-4 text-xs text-gray-400">Aug – Feb, cohort average</p>
          <PerformanceTrendChart data={TREND_DATA} attendanceThreshold={75} />
        </div>
      </div>

      {/* Row 2: Department risk bar + High-risk flags list */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Department risk bar chart (wider) */}
        <div className="card p-6 lg:col-span-3">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            Department-wise Risk
          </h2>
          <p className="mb-4 text-xs text-gray-400">
            Total vs high-risk students per department
          </p>
          <DepartmentRiskChart data={deptData} />
        </div>

        {/* Recent high-risk flags */}
        <div className="card flex flex-col p-6 lg:col-span-2">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            Recent High-Risk Flags
          </h2>
          <p className="mb-4 text-xs text-gray-400">
            Latest model predictions flagged HIGH
          </p>

          <ul className="flex flex-col divide-y divide-gray-100">
            {flaggedStudents.map((p) => {
              const initial = p.student_name.charAt(0).toUpperCase();
              const topFactor = p.contributing_factors[0]?.feature ?? "—";
              const scoreVal = Math.round(p.risk_score * 100);

              return (
                <li key={p.student_id} className="flex items-center gap-3 py-3">
                  {/* Avatar */}
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700">
                    {initial}
                  </div>

                  {/* Info */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">
                      {p.student_name}
                    </p>
                    <p className="truncate text-xs text-gray-500">{topFactor}</p>
                  </div>

                  {/* Score + badge */}
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-xs font-semibold text-red-600">
                      {scoreVal}%
                    </span>
                    <RiskBadge label={p.risk_label} size="sm" />
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="mt-auto pt-4">
            <a
              href="/dashboard/faculty"
              className="block text-center text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              View all at-risk students →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
