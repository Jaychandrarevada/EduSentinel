"use client";

// ─────────────────────────────────────────────
//  Faculty Dashboard – At-Risk & All Students
// ─────────────────────────────────────────────
import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  Users,
  AlertTriangle,
  ChevronRight,
  BarChart2,
} from "lucide-react";
import RiskBadge from "@/components/dashboard/RiskBadge";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { usePredictions } from "@/hooks/usePredictions";
import { useStudents } from "@/hooks/useStudents";
import { formatDate } from "@/lib/utils";
import type { RiskLabel } from "@/types";

// ── Types ─────────────────────────────────────
type RiskFilter = "ALL" | RiskLabel;
type Tab = "at-risk" | "all";

// ── Risk score progress bar ────────────────────
function RiskScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? "bg-red-500" : pct >= 40 ? "bg-amber-400" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-9 text-right text-xs font-medium tabular-nums text-gray-700">
        {pct}%
      </span>
    </div>
  );
}

// ── Component ─────────────────────────────────
export default function FacultyDashboardPage() {
  const [activeTab, setActiveTab] = useState<Tab>("at-risk");
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("ALL");

  // ── At-risk tab data ──
  const { data: predictionsData, loading: predictionsLoading } = usePredictions(
    {
      risk_label: riskFilter === "ALL" ? undefined : riskFilter,
      size: 50,
    }
  );

  // ── All students tab data ──
  const { data: studentsData, loading: studentsLoading } = useStudents({
    search: searchQuery.trim() || undefined,
    size: 50,
  });

  // Client-side search filter for at-risk tab
  const filteredPredictions = useMemo(() => {
    const items = predictionsData?.items ?? [];
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter((p) => p.student_name.toLowerCase().includes(q));
  }, [predictionsData, searchQuery]);

  const riskFilters: RiskFilter[] = ["ALL", "HIGH", "MEDIUM", "LOW"];

  const riskFilterStyles: Record<RiskFilter, string> = {
    ALL: "bg-gray-100 text-gray-700 hover:bg-gray-200",
    HIGH: "bg-red-50 text-red-700 hover:bg-red-100 ring-1 ring-red-200",
    MEDIUM: "bg-amber-50 text-amber-700 hover:bg-amber-100 ring-1 ring-amber-200",
    LOW: "bg-green-50 text-green-700 hover:bg-green-100 ring-1 ring-green-200",
  };

  const activeRiskStyle: Record<RiskFilter, string> = {
    ALL: "bg-gray-700 text-white",
    HIGH: "bg-red-600 text-white ring-0",
    MEDIUM: "bg-amber-500 text-white ring-0",
    LOW: "bg-green-600 text-white ring-0",
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Students</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Monitor at-risk flags and browse your complete student roster.
        </p>
      </div>

      {/* Tab bar + controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Tabs */}
        <div className="flex rounded-xl bg-gray-100 p-1">
          <button
            onClick={() => setActiveTab("at-risk")}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              activeTab === "at-risk"
                ? "bg-white text-indigo-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            At Risk
            {predictionsData && (
              <span className="ml-1 rounded-full bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">
                {predictionsData.total}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("all")}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              activeTab === "all"
                ? "bg-white text-indigo-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <Users className="h-4 w-4" />
            All Students
            {studentsData && (
              <span className="ml-1 rounded-full bg-gray-200 px-1.5 py-0.5 text-xs font-semibold text-gray-600">
                {studentsData.total}
              </span>
            )}
          </button>
        </div>

        {/* Search */}
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search students…"
            className="input pl-9"
          />
        </div>
      </div>

      {/* Risk filter buttons (at-risk tab only) */}
      {activeTab === "at-risk" && (
        <div className="flex flex-wrap gap-2">
          {riskFilters.map((f) => (
            <button
              key={f}
              onClick={() => setRiskFilter(f)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                riskFilter === f
                  ? activeRiskStyle[f]
                  : riskFilterStyles[f]
              }`}
            >
              {f === "ALL" ? "All Levels" : f.charAt(0) + f.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      )}

      {/* ── AT-RISK TAB ── */}
      {activeTab === "at-risk" && (
        <>
          {predictionsLoading ? (
            <PageLoading />
          ) : filteredPredictions.length === 0 ? (
            <EmptyState
              icon={AlertTriangle}
              title="No at-risk students found"
              description={
                riskFilter !== "ALL"
                  ? `No students flagged as ${riskFilter.toLowerCase()} risk for the current filters.`
                  : "All students appear to be on track."
              }
            />
          ) : (
            <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100">
                  <thead>
                    <tr className="table-header">
                      <th className="px-6 py-3 text-left">Student</th>
                      <th className="px-6 py-3 text-left">Risk Score</th>
                      <th className="px-6 py-3 text-left">Risk Level</th>
                      <th className="px-6 py-3 text-left">Top Factor</th>
                      <th className="px-6 py-3 text-left">Predicted At</th>
                      <th className="px-6 py-3 text-left">Analytics</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50 text-sm">
                    {filteredPredictions.map((p) => {
                      const initial = (p.student_name ?? "?").charAt(0).toUpperCase();
                      const topFactor =
                        p.contributing_factors[0]?.feature ?? "—";
                      return (
                        <tr
                          key={p.student_id}
                          className="hover:bg-gray-50/60 transition-colors"
                        >
                          {/* Student */}
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
                                {initial}
                              </div>
                              <span className="font-medium text-gray-900">
                                {p.student_name}
                              </span>
                            </div>
                          </td>
                          {/* Score bar */}
                          <td className="px-6 py-4">
                            <RiskScoreBar score={p.risk_score} />
                          </td>
                          {/* Risk badge */}
                          <td className="px-6 py-4">
                            <RiskBadge label={p.risk_label} />
                          </td>
                          {/* Top factor */}
                          <td className="px-6 py-4 text-gray-600">{topFactor}</td>
                          {/* Predicted at */}
                          <td className="px-6 py-4 text-gray-400">
                            {formatDate(p.predicted_at)}
                          </td>
                          {/* Link */}
                          <td className="px-6 py-4">
                            <Link
                              href={`/dashboard/analytics/${p.student_id}`}
                              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
                            >
                              View <ChevronRight className="h-3 w-3" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── ALL STUDENTS TAB ── */}
      {activeTab === "all" && (
        <>
          {studentsLoading ? (
            <PageLoading />
          ) : !studentsData || studentsData.items.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No students found"
              description={
                searchQuery
                  ? `No results for "${searchQuery}".`
                  : "No students are assigned to your courses yet."
              }
            />
          ) : (
            <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-100">
                  <thead>
                    <tr className="table-header">
                      <th className="px-6 py-3 text-left">Roll No</th>
                      <th className="px-6 py-3 text-left">Name</th>
                      <th className="px-6 py-3 text-left">Department</th>
                      <th className="px-6 py-3 text-left">Semester</th>
                      <th className="px-6 py-3 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50 text-sm">
                    {studentsData.items.map((s) => (
                      <tr
                        key={s.id}
                        className="hover:bg-gray-50/60 transition-colors"
                      >
                        <td className="px-6 py-4 font-mono text-xs text-gray-500">
                          {s.roll_no}
                        </td>
                        <td className="px-6 py-4 font-medium text-gray-900">
                          {s.full_name}
                        </td>
                        <td className="px-6 py-4 text-gray-600">
                          {s.department}
                        </td>
                        <td className="px-6 py-4 text-gray-600">
                          Sem {s.semester}
                        </td>
                        <td className="px-6 py-4">
                          <Link
                            href={`/dashboard/analytics/${s.id}`}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
                          >
                            <BarChart2 className="h-3.5 w-3.5" />
                            View Analytics
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination hint */}
              {studentsData.pages > 1 && (
                <div className="border-t border-gray-100 px-6 py-3 text-xs text-gray-400">
                  Showing {studentsData.items.length} of {studentsData.total} students
                  &nbsp;&mdash;&nbsp;use the Analytics page for full pagination.
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
