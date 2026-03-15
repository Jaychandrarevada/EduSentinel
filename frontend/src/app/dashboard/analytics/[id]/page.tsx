"use client";

// ─────────────────────────────────────────────
//  Student Analytics Detail Page
// ─────────────────────────────────────────────
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, User, BookOpen, Activity, Monitor } from "lucide-react";
import RiskBadge from "@/components/dashboard/RiskBadge";
import AttendanceBarChart from "@/components/charts/AttendanceBarChart";
import type { AttendancePoint } from "@/components/charts/AttendanceBarChart";
import AssignmentScoreChart from "@/components/charts/AssignmentScoreChart";
import type { AssignmentPoint } from "@/components/charts/AssignmentScoreChart";
import LmsActivityChart from "@/components/charts/LmsActivityChart";
import type { LmsPoint } from "@/components/charts/LmsActivityChart";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import { useStudentPerformance } from "@/hooks/useStudents";
import { formatPct } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ── Fallback chart data ───────────────────────

const ATTENDANCE_FALLBACK: AttendancePoint[] = [
  { month: "Jan", pct: 82 },
  { month: "Feb", pct: 77 },
  { month: "Mar", pct: 71 },
  { month: "Apr", pct: 65 },
  { month: "May", pct: 68 },
  { month: "Jun", pct: 74 },
];

const ASSIGNMENT_FALLBACK: AssignmentPoint[] = [
  { name: "A1", score: 78, max_score: 100, is_late: false },
  { name: "A2", score: 62, max_score: 100, is_late: false },
  { name: "A3", score: 45, max_score: 100, is_late: true },
  { name: "A4", score: 55, max_score: 100, is_late: false },
  { name: "A5", score: 38, max_score: 100, is_late: true },
  { name: "A6", score: 60, max_score: 100, is_late: false },
];

const LMS_FALLBACK: LmsPoint[] = [
  { week: "W1", logins: 12, views: 34, hours: 5 },
  { week: "W2", logins: 10, views: 28, hours: 4 },
  { week: "W3", logins: 7,  views: 19, hours: 3 },
  { week: "W4", logins: 5,  views: 14, hours: 2 },
  { week: "W5", logins: 4,  views: 10, hours: 1 },
  { week: "W6", logins: 6,  views: 16, hours: 2 },
  { week: "W7", logins: 8,  views: 22, hours: 3 },
  { week: "W8", logins: 9,  views: 26, hours: 4 },
];

// ── Metric badge card ─────────────────────────
interface MetricBadgeProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  color: string;
  subtext?: string;
}

function MetricBadge({ label, value, icon, color, subtext }: MetricBadgeProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white p-4 ring-1 ring-gray-200 shadow-sm">
      <div className={cn("flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl", color)}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-bold text-gray-900">{value}</p>
        {subtext && <p className="text-xs text-gray-400">{subtext}</p>}
      </div>
    </div>
  );
}

// ── Circular score ring ───────────────────────
function ScoreRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - score);
  const color = pct >= 70 ? "#ef4444" : pct >= 40 ? "#f59e0b" : "#22c55e";

  return (
    <div className="relative flex h-28 w-28 items-center justify-center">
      <svg className="-rotate-90" width="112" height="112" viewBox="0 0 112 112">
        <circle cx="56" cy="56" r={radius} fill="none" stroke="#f3f4f6" strokeWidth="10" />
        <circle
          cx="56"
          cy="56"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-bold text-gray-900">{pct}%</span>
        <span className="text-[10px] text-gray-400 uppercase tracking-wide">Risk</span>
      </div>
    </div>
  );
}

// ── Impact bar ────────────────────────────────
function ImpactBar({ feature, impact }: { feature: string; impact: number }) {
  const pct = Math.min(Math.round(impact * 100), 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-700 font-medium">{feature}</span>
        <span className="text-gray-500">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-indigo-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Page component ────────────────────────────
export default function StudentAnalyticsPage() {
  const params = useParams();
  const router = useRouter();
  const studentId = params?.id ? Number(params.id) : null;

  const { data, loading, error } = useStudentPerformance(studentId);

  if (loading) return <PageLoading />;

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-sm font-medium text-gray-500">
          {error
            ? "Failed to load student data. The API may not be available."
            : "Student not found."}
        </p>
        <button onClick={() => router.back()} className="btn-secondary mt-4">
          Go back
        </button>
      </div>
    );
  }

  const pred = data.latest_prediction;
  const riskLabel = pred?.risk_label ?? "LOW";
  const riskScore = pred?.risk_score ?? 0;
  const factors = pred?.contributing_factors ?? [];

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

      {/* Student info card */}
      <div className="card p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            {/* Avatar */}
            <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-xl font-bold text-white shadow-md">
              {(data.full_name ?? "?").charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{data.full_name}</h1>
              <p className="mt-0.5 text-sm text-gray-500">
                {data.roll_no} &nbsp;&middot;&nbsp; {data.department} &nbsp;&middot;&nbsp; Semester {data.semester}
              </p>
            </div>
          </div>

          {pred && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span>Last prediction:</span>
              <span className="font-medium text-gray-700">
                {new Date(pred.predicted_at).toLocaleDateString("en-IN", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Metric badges */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricBadge
          label="Attendance"
          value={formatPct(data.attendance_pct)}
          icon={<Activity className="h-5 w-5 text-indigo-600" />}
          color="bg-indigo-50"
          subtext={data.attendance_pct >= 75 ? "Above threshold" : "Below 75% threshold"}
        />
        <MetricBadge
          label="Avg Marks"
          value={formatPct(data.avg_marks_pct)}
          icon={<BookOpen className="h-5 w-5 text-emerald-600" />}
          color="bg-emerald-50"
          subtext={data.avg_marks_pct >= 50 ? "Passing" : "Below passing"}
        />
        <MetricBadge
          label="Assignment Completion"
          value={formatPct(data.assignment_completion_rate * 100)}
          icon={<User className="h-5 w-5 text-violet-600" />}
          color="bg-violet-50"
          subtext={`${Math.round(data.assignment_completion_rate * 100)}% submitted`}
        />
        <MetricBadge
          label="LMS Engagement"
          value={data.lms_engagement_score.toFixed(1)}
          icon={<Monitor className="h-5 w-5 text-amber-600" />}
          color="bg-amber-50"
          subtext="Engagement score (0–100)"
        />
      </div>

      {/* Risk prediction card */}
      <div className="card p-6">
        <h2 className="mb-4 text-base font-semibold text-gray-800">
          Risk Prediction
        </h2>
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start">
          {/* Circular score */}
          <div className="flex flex-col items-center gap-3">
            <ScoreRing score={riskScore} />
            <RiskBadge label={riskLabel} size="md" />
          </div>

          {/* Contributing factors */}
          <div className="flex-1 space-y-3">
            <h3 className="text-sm font-medium text-gray-700">
              Contributing Factors
            </h3>
            {factors.length > 0 ? (
              factors
                .slice()
                .sort((a, b) => b.impact - a.impact)
                .map((f) => (
                  <ImpactBar
                    key={f.feature}
                    feature={f.feature}
                    impact={f.impact}
                  />
                ))
            ) : (
              <p className="text-sm text-gray-400">
                No contributing factors available.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Attendance */}
        <div className="card p-6">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            Monthly Attendance
          </h2>
          <p className="mb-4 text-xs text-gray-400">Jan – Jun (indicative)</p>
          <AttendanceBarChart data={ATTENDANCE_FALLBACK} threshold={75} />
        </div>

        {/* Assignments */}
        <div className="card p-6">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            Assignment Scores
          </h2>
          <p className="mb-4 text-xs text-gray-400">
            Orange bars = late submission
          </p>
          <AssignmentScoreChart data={ASSIGNMENT_FALLBACK} />
        </div>

        {/* LMS Activity (full width) */}
        <div className="card p-6 lg:col-span-2">
          <h2 className="mb-1 text-base font-semibold text-gray-800">
            LMS Activity
          </h2>
          <p className="mb-4 text-xs text-gray-400">
            Weekly logins and content views
          </p>
          <LmsActivityChart data={LMS_FALLBACK} />
        </div>
      </div>
    </div>
  );
}
