"use client";

// ─────────────────────────────────────────────
//  Analytics Overview – Searchable Student List
// ─────────────────────────────────────────────
import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  BarChart2,
  Users,
} from "lucide-react";
import RiskBadge from "@/components/dashboard/RiskBadge";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { useStudents } from "@/hooks/useStudents";
import { usePredictions } from "@/hooks/usePredictions";
import type { Prediction } from "@/types";

// ── Fallback data ─────────────────────────────
const FALLBACK_STUDENTS = [
  { id: 1, roll_no: "CS21001", full_name: "Aarav Sharma",   department: "CSE",   semester: 5, batch_year: 2021, email: "" },
  { id: 2, roll_no: "CS21002", full_name: "Priya Nair",     department: "CSE",   semester: 5, batch_year: 2021, email: "" },
  { id: 3, roll_no: "EC21010", full_name: "Rohan Mehta",    department: "ECE",   semester: 5, batch_year: 2021, email: "" },
  { id: 4, roll_no: "ME21020", full_name: "Sneha Pillai",   department: "MECH",  semester: 3, batch_year: 2022, email: "" },
  { id: 5, roll_no: "IT21030", full_name: "Karan Joshi",    department: "IT",    semester: 5, batch_year: 2021, email: "" },
  { id: 6, roll_no: "CV21040", full_name: "Divya Rao",      department: "CIVIL", semester: 3, batch_year: 2022, email: "" },
];

const PAGE_SIZE = 12;

// ── Student card ─────────────────────────────
interface StudentCardProps {
  id: number;
  rollNo: string;
  name: string;
  department: string;
  semester: number;
  prediction?: Prediction;
}

function StudentCard({
  id,
  rollNo,
  name,
  department,
  semester,
  prediction,
}: StudentCardProps) {
  const initial = name.charAt(0).toUpperCase();

  return (
    <Link
      href={`/dashboard/analytics/${id}`}
      className="card group flex flex-col gap-4 p-5 transition-all hover:shadow-md hover:ring-indigo-200"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-sm font-bold text-indigo-700 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
            {initial}
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold text-gray-900 text-sm">{name}</p>
            <p className="text-xs text-gray-500 font-mono">{rollNo}</p>
          </div>
        </div>
        {prediction ? (
          <RiskBadge label={prediction.risk_label} size="sm" />
        ) : (
          <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-400">
            No data
          </span>
        )}
      </div>

      {/* Meta row */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          {department} &nbsp;&middot;&nbsp; Sem {semester}
        </span>
        {prediction && (
          <span className="font-medium text-gray-700 tabular-nums">
            {Math.round(prediction.risk_score * 100)}% risk
          </span>
        )}
      </div>

      {/* Risk score bar */}
      {prediction && (
        <div className="h-1 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full transition-all ${
              prediction.risk_label === "HIGH"
                ? "bg-red-500"
                : prediction.risk_label === "MEDIUM"
                ? "bg-amber-400"
                : "bg-green-500"
            }`}
            style={{ width: `${Math.round(prediction.risk_score * 100)}%` }}
          />
        </div>
      )}

      {/* CTA */}
      <div className="flex items-center gap-1 text-xs font-medium text-indigo-600 group-hover:text-indigo-800 transition-colors">
        <BarChart2 className="h-3.5 w-3.5" />
        View Analytics
      </div>
    </Link>
  );
}

// ── Page component ────────────────────────────
export default function AnalyticsOverviewPage() {
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);

  // Debounce search input
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPage(1);
    clearTimeout((window as Window & { _searchTimeout?: number })._searchTimeout);
    (window as Window & { _searchTimeout?: number })._searchTimeout = window.setTimeout(() => {
      setDebouncedSearch(value);
    }, 350);
  };

  const { data: studentsData, loading: studentsLoading } = useStudents({
    search: debouncedSearch.trim() || undefined,
    page,
    size: PAGE_SIZE,
  });

  // Fetch latest predictions to overlay risk labels on cards
  const { data: predictionsData } = usePredictions({ size: 100 });

  // Build a lookup map: student_id -> Prediction
  const predictionMap = useMemo(() => {
    const map = new Map<number, Prediction>();
    if (predictionsData?.items) {
      for (const p of predictionsData.items) {
        map.set(p.student_id, p);
      }
    }
    return map;
  }, [predictionsData]);

  const students =
    studentsData && studentsData.items.length > 0
      ? studentsData.items
      : !studentsLoading
      ? FALLBACK_STUDENTS
      : [];

  const totalPages = studentsData?.pages ?? 1;
  const totalCount = studentsData?.total ?? FALLBACK_STUDENTS.length;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Search and explore individual student performance data.
        </p>
      </div>

      {/* Search bar + count */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search by name or roll number…"
            className="input pl-9"
          />
        </div>

        {!studentsLoading && (
          <p className="text-sm text-gray-500">
            {totalCount.toLocaleString()} student{totalCount !== 1 ? "s" : ""}
            {debouncedSearch && (
              <span className="ml-1 font-medium">
                matching &ldquo;{debouncedSearch}&rdquo;
              </span>
            )}
          </p>
        )}
      </div>

      {/* Content */}
      {studentsLoading ? (
        <PageLoading />
      ) : students.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No students found"
          description={
            debouncedSearch
              ? `No results for "${debouncedSearch}". Try a different search.`
              : "No students are available in this system."
          }
        />
      ) : (
        <>
          {/* Student cards grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {students.map((s) => (
              <StudentCard
                key={s.id}
                id={s.id}
                rollNo={s.roll_no}
                name={s.full_name}
                department={s.department}
                semester={s.semester}
                prediction={predictionMap.get(s.id)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-200 pt-4">
              <p className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </p>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="btn-secondary flex items-center gap-1 px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Previous
                </button>

                {/* Page number pills */}
                <div className="hidden sm:flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const half = Math.floor(Math.min(5, totalPages) / 2);
                    let startPage = Math.max(1, page - half);
                    const endPage = Math.min(totalPages, startPage + Math.min(5, totalPages) - 1);
                    startPage = Math.max(1, endPage - Math.min(5, totalPages) + 1);
                    const pageNum = startPage + i;
                    if (pageNum > totalPages) return null;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium transition-colors ${
                          pageNum === page
                            ? "bg-indigo-600 text-white"
                            : "text-gray-600 hover:bg-gray-100"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="btn-secondary flex items-center gap-1 px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
