"use client";

// ─────────────────────────────────────────────
//  Faculty → Alerts — at-risk notifications
// ─────────────────────────────────────────────
import { useState, useEffect } from "react";
import { Bell, CheckCircle, AlertTriangle, Filter } from "lucide-react";
import RiskBadge from "@/components/dashboard/RiskBadge";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";
import api from "@/lib/api";

interface AlertItem {
  id: number;
  student_id: number;
  student_name: string;
  alert_type: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  message: string;
  is_resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  HIGH:   "border-l-red-500 bg-red-50/40",
  MEDIUM: "border-l-amber-400 bg-amber-50/40",
  LOW:    "border-l-emerald-400 bg-emerald-50/40",
};

export default function FacultyAlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"unresolved" | "all">("unresolved");
  const [resolving, setResolving] = useState<number | null>(null);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const r = await api.get("/predictions/alerts", {
        params: { is_resolved: filter === "all" ? undefined : false, size: 50 },
      });
      setAlerts(r.data.items ?? r.data ?? []);
    } catch {
      // Fallback demo data
      setAlerts(([
        { id: 1, student_id: 101, student_name: "Aarav Sharma", alert_type: "HIGH_RISK_PREDICTED", severity: "HIGH" as const, message: "Student predicted HIGH risk (score: 91%) in Sem 5. Top factor: Low Attendance.", is_resolved: false, resolved_at: null, created_at: "2024-03-10T08:00:00Z" },
        { id: 2, student_id: 102, student_name: "Priya Nair", alert_type: "HIGH_RISK_PREDICTED", severity: "HIGH" as const, message: "Student predicted HIGH risk (score: 85%) in Sem 5. Top factor: Missed Assignments.", is_resolved: false, resolved_at: null, created_at: "2024-03-10T08:00:00Z" },
        { id: 3, student_id: 103, student_name: "Rohan Mehta", alert_type: "HIGH_RISK_PREDICTED", severity: "MEDIUM" as const, message: "Student predicted MEDIUM risk (score: 48%) in Sem 5. Top factor: Low LMS engagement.", is_resolved: true, resolved_at: "2024-03-11T10:00:00Z", created_at: "2024-03-09T08:00:00Z" },
      ] as AlertItem[]).filter((a) => filter === "all" || !a.is_resolved));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAlerts(); }, [filter]);

  const handleResolve = async (alertId: number) => {
    setResolving(alertId);
    try {
      await api.patch(`/predictions/alerts/${alertId}/resolve`);
      fetchAlerts();
    } catch {
      // silently fail — API may not be running in dev
    } finally {
      setResolving(null);
    }
  };

  const unresolvedCount = alerts.filter((a) => !a.is_resolved).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
            {unresolvedCount > 0 && (
              <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-700">
                {unresolvedCount}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-gray-500">
            At-risk notifications for your assigned students
          </p>
        </div>

        {/* Filter toggle */}
        <div className="flex items-center gap-1 rounded-xl bg-gray-100 p-1">
          <button
            onClick={() => setFilter("unresolved")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${filter === "unresolved" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"}`}
          >
            <AlertTriangle className="h-3.5 w-3.5" /> Unresolved
          </button>
          <button
            onClick={() => setFilter("all")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${filter === "all" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"}`}
          >
            <Filter className="h-3.5 w-3.5" /> All
          </button>
        </div>
      </div>

      {/* Alert list */}
      {loading ? (
        <PageLoading />
      ) : alerts.length === 0 ? (
        <EmptyState
          icon={Bell}
          title={filter === "unresolved" ? "No unresolved alerts" : "No alerts"}
          description={filter === "unresolved" ? "All caught up! No unresolved at-risk flags." : "No alerts found for your students."}
        />
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`rounded-xl border-l-4 p-5 ring-1 ring-gray-200 shadow-sm ${SEVERITY_COLORS[alert.severity] ?? "bg-white"} ${alert.is_resolved ? "opacity-60" : ""}`}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-gray-900">{alert.student_name}</span>
                    <RiskBadge label={alert.severity} size="sm" />
                    {alert.is_resolved && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                        <CheckCircle className="h-3 w-3" /> Resolved
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-sm text-gray-600">{alert.message}</p>
                  <p className="mt-1 text-xs text-gray-400">
                    Flagged {formatDate(alert.created_at)}
                    {alert.resolved_at && ` · Resolved ${formatDate(alert.resolved_at)}`}
                  </p>
                </div>

                {!alert.is_resolved && (
                  <button
                    onClick={() => handleResolve(alert.id)}
                    disabled={resolving === alert.id}
                    className="flex shrink-0 items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-gray-200 hover:bg-emerald-50 hover:text-emerald-700 hover:ring-emerald-200 transition-colors disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4" />
                    {resolving === alert.id ? "Resolving…" : "Mark Resolved"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
