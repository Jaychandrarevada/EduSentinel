import { useEffect, useState } from "react";
import api from "@/lib/api";
import { CohortSummary } from "@/types";

export interface DepartmentStat {
  department: string;
  total_students: number;
  high_risk_count: number;
  avg_attendance_pct: number;
  avg_marks_pct: number;
}

export function useCohortOverview(semester?: string) {
  const [data, setData] = useState<CohortSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/analytics/cohort-overview", { params: semester ? { semester } : {} })
      .then((r) => setData(r.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [semester]);

  return { data, loading, error };
}

export function useDepartmentStats(semester?: string) {
  const [data, setData] = useState<DepartmentStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/analytics/department-stats", { params: semester ? { semester } : {} })
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [semester]);

  return { data, loading };
}

export function usePredictionSummary(semester?: string) {
  const [data, setData] = useState<{
    total_students: number;
    high_risk_count: number;
    medium_risk_count: number;
    low_risk_count: number;
    high_risk_pct: number;
    last_run_at: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/predictions/summary", { params: semester ? { semester } : {} })
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [semester]);

  return { data, loading };
}
