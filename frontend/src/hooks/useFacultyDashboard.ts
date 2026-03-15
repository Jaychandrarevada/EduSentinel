import { useEffect, useState } from "react";
import api from "@/lib/api";

export interface SubjectPerformance {
  course_id: number;
  course_name: string;
  student_count: number;
  avg_attendance_pct: number;
  avg_marks_pct: number;
}

export interface FacultyDashboardData {
  stats: {
    total_students: number;
    at_risk_count: number;
    avg_attendance_pct: number;
    avg_assignment_score: number;
  };
  risk_distribution: { HIGH: number; MEDIUM: number; LOW: number };
  subject_performance: SubjectPerformance[];
}

export interface StudentSummary {
  id: number;
  roll_no: string;
  full_name: string;
  department: string;
  semester: number;
  attendance_pct: number;
  marks_pct: number;
  assignment_pct: number;
  risk_label: "HIGH" | "MEDIUM" | "LOW" | null;
  risk_score: number | null;
}

export interface StudentSummaryPage {
  items: StudentSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export function useFacultyDashboard() {
  const [data, setData] = useState<FacultyDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/faculty/me/dashboard")
      .then((r) => setData(r.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}

export function useStudentsSummary(filters: {
  search?: string;
  risk_label?: string;
  page?: number;
  size?: number;
} = {}) {
  const [data, setData] = useState<StudentSummaryPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api
      .get("/faculty/me/students-summary", { params: filters, signal: controller.signal })
      .then((r) => setData(r.data))
      .catch((err) => { if (err.name !== "CanceledError") setError(err.message); })
      .finally(() => setLoading(false));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  return { data, loading, error };
}
