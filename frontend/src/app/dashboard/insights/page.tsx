"use client";

// ─────────────────────────────────────────────
//  Visual Analytics / Insights Page
//  Five interactive cohort-level charts
// ─────────────────────────────────────────────
import { useState } from "react";
import { BarChart2, TrendingUp, Users, BookOpen, Activity } from "lucide-react";
import RiskDistributionAnalytics from "@/components/charts/RiskDistributionAnalytics";
import AttendanceVsPerformanceChart from "@/components/charts/AttendanceVsPerformanceChart";
import AssignmentScoreTimelineChart from "@/components/charts/AssignmentScoreTimelineChart";
import LmsEngagementTrendChart from "@/components/charts/LmsEngagementTrendChart";
import PredictedRiskCategoriesChart from "@/components/charts/PredictedRiskCategoriesChart";
import { useCohortOverview, useDepartmentStats } from "@/hooks/useAnalytics";
import type { DepartmentStat } from "@/hooks/useAnalytics";
import type { ScatterStudent } from "@/components/charts/AttendanceVsPerformanceChart";
import type { AssignmentTimelinePoint } from "@/components/charts/AssignmentScoreTimelineChart";
import type { LmsEngagementPoint } from "@/components/charts/LmsEngagementTrendChart";
import type { RiskCategoryPoint } from "@/components/charts/PredictedRiskCategoriesChart";

// ── Fallback / demo data ───────────────────────

const SCATTER_FALLBACK: ScatterStudent[] = [
  { student_name: "Aarav Sharma",   attendance_pct: 48, avg_marks_pct: 41, risk_label: "HIGH" },
  { student_name: "Priya Nair",     attendance_pct: 54, avg_marks_pct: 47, risk_label: "HIGH" },
  { student_name: "Rohan Mehta",    attendance_pct: 62, avg_marks_pct: 55, risk_label: "MEDIUM" },
  { student_name: "Sneha Pillai",   attendance_pct: 71, avg_marks_pct: 63, risk_label: "MEDIUM" },
  { student_name: "Karan Joshi",    attendance_pct: 80, avg_marks_pct: 74, risk_label: "LOW" },
  { student_name: "Divya Rao",      attendance_pct: 88, avg_marks_pct: 82, risk_label: "LOW" },
  { student_name: "Vikram Singh",   attendance_pct: 45, avg_marks_pct: 38, risk_label: "HIGH" },
  { student_name: "Anjali Menon",   attendance_pct: 66, avg_marks_pct: 60, risk_label: "MEDIUM" },
  { student_name: "Rahul Gupta",    attendance_pct: 77, avg_marks_pct: 70, risk_label: "LOW" },
  { student_name: "Neha Verma",     attendance_pct: 55, avg_marks_pct: 49, risk_label: "HIGH" },
  { student_name: "Arjun Patel",    attendance_pct: 83, avg_marks_pct: 78, risk_label: "LOW" },
  { student_name: "Pooja Iyer",     attendance_pct: 68, avg_marks_pct: 62, risk_label: "MEDIUM" },
  { student_name: "Siddharth Roy",  attendance_pct: 40, avg_marks_pct: 35, risk_label: "HIGH" },
  { student_name: "Meera Krishnan", attendance_pct: 91, avg_marks_pct: 85, risk_label: "LOW" },
  { student_name: "Tarun Bose",     attendance_pct: 72, avg_marks_pct: 66, risk_label: "MEDIUM" },
];

const ASSIGNMENT_FALLBACK: AssignmentTimelinePoint[] = [
  { label: "A1",  score: 72, max_score: 100, is_late: false, submitted: true },
  { label: "A2",  score: 65, max_score: 100, is_late: false, submitted: true },
  { label: "A3",  score: 45, max_score: 100, is_late: true,  submitted: true },
  { label: "A4",  score: 0,  max_score: 100, is_late: false, submitted: false },
  { label: "A5",  score: 58, max_score: 100, is_late: false, submitted: true },
  { label: "A6",  score: 48, max_score: 100, is_late: true,  submitted: true },
  { label: "A7",  score: 70, max_score: 100, is_late: false, submitted: true },
  { label: "A8",  score: 82, max_score: 100, is_late: false, submitted: true },
];

const LMS_FALLBACK: LmsEngagementPoint[] = [
  { period: "W1", logins: 18, content_views: 42, hours_spent: 6.5,  forum_posts: 3 },
  { period: "W2", logins: 22, content_views: 55, hours_spent: 8.0,  forum_posts: 5 },
  { period: "W3", logins: 15, content_views: 38, hours_spent: 5.0,  forum_posts: 2 },
  { period: "W4", logins: 10, content_views: 29, hours_spent: 3.5,  forum_posts: 1 },
  { period: "W5", logins: 8,  content_views: 22, hours_spent: 2.5,  forum_posts: 1 },
  { period: "W6", logins: 6,  content_views: 18, hours_spent: 1.5,  forum_posts: 0 },
  { period: "W7", logins: 12, content_views: 33, hours_spent: 4.0,  forum_posts: 2 },
  { period: "W8", logins: 20, content_views: 48, hours_spent: 7.0,  forum_posts: 4 },
];

const RISK_CATEGORY_FALLBACK: RiskCategoryPoint[] = [
  { group: "CSE",   high: 42, medium: 78, low: 200, total: 320 },
  { group: "ECE",   high: 35, medium: 70, low: 175, total: 280 },
  { group: "MECH",  high: 28, medium: 55, low: 127, total: 210 },
  { group: "CIVIL", high: 20, medium: 48, low: 122, total: 190 },
  { group: "IT",    high: 31, medium: 62, low: 147, total: 240 },
];

const SEMESTERS = ["All", "Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"];

// ── Section card wrapper ───────────────────────
function ChartCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-6">
      <div className="mb-1 flex items-center gap-2">
        <Icon className="h-4 w-4 text-indigo-500" />
        <h2 className="text-base font-semibold text-gray-800">{title}</h2>
      </div>
      <p className="mb-5 text-xs text-gray-400">{description}</p>
      {children}
    </div>
  );
}

// ── Page ──────────────────────────────────────
export default function InsightsPage() {
  const [semester, setSemester] = useState("All");
  const semParam = semester === "All" ? undefined : semester;

  const { data: cohort } = useCohortOverview(semParam);
  const { data: deptStats } = useDepartmentStats(semParam);

  // Resolve risk distribution from live data or fallback
  const riskDist = {
    high:   cohort?.high_risk_count   ?? 87,
    medium: cohort?.medium_risk_count ?? 193,
    low:    cohort?.low_risk_count    ?? 960,
  };

  // Build RiskCategoryPoint from dept stats or fallback
  const riskCategoryData: RiskCategoryPoint[] =
    deptStats && deptStats.length > 0
      ? deptStats.map((d: DepartmentStat) => ({
          group:  d.department,
          high:   d.high_risk_count,
          medium: Math.round(d.total_students * 0.25),
          low:    d.total_students - d.high_risk_count - Math.round(d.total_students * 0.25),
          total:  d.total_students,
        }))
      : RISK_CATEGORY_FALLBACK;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Visual Insights</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Interactive cohort-level analytics across five dimensions
          </p>
        </div>
        <select
          value={semester}
          onChange={(e) => setSemester(e.target.value)}
          className="input w-36"
        >
          {SEMESTERS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Row 1: Risk distribution (full width) */}
      <ChartCard
        icon={BarChart2}
        title="Risk Distribution"
        description="Breakdown of students by predicted risk level for the selected cohort"
      >
        <RiskDistributionAnalytics data={riskDist} />
      </ChartCard>

      {/* Row 2: Attendance vs Performance + Predicted Risk Categories */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          icon={Users}
          title="Attendance vs Performance"
          description="Scatter plot correlating attendance % with marks % — each dot is a student"
        >
          <AttendanceVsPerformanceChart data={SCATTER_FALLBACK} />
        </ChartCard>

        <ChartCard
          icon={TrendingUp}
          title="Predicted Risk Categories"
          description="Stacked student counts by risk level per department — dashed line shows high-risk %"
        >
          <PredictedRiskCategoriesChart data={riskCategoryData} groupLabel="Department" />
        </ChartCard>
      </div>

      {/* Row 3: Assignment timeline + LMS engagement trend */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          icon={BookOpen}
          title="Assignment Score Timeline"
          description="Score per assignment with on-time / late / missing indicators and rolling average"
        >
          <AssignmentScoreTimelineChart data={ASSIGNMENT_FALLBACK} />
        </ChartCard>

        <ChartCard
          icon={Activity}
          title="LMS Engagement Trend"
          description="Weekly LMS activity — toggle metrics to compare logins, views, hours, and forum posts"
        >
          <LmsEngagementTrendChart data={LMS_FALLBACK} />
        </ChartCard>
      </div>
    </div>
  );
}
