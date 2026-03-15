import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Student, PaginatedResponse } from "@/types";

interface Filters {
  department?: string;
  semester?: number;
  search?: string;
  page?: number;
  size?: number;
}

export function useStudents(filters: Filters = {}) {
  const [data, setData] = useState<PaginatedResponse<Student> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuthStore();

  // Faculty see only their enrolled students; admins see everyone
  const endpoint =
    user?.role === "FACULTY" ? "/faculty/me/students" : "/students";

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api
      .get(endpoint, { params: filters, signal: controller.signal })
      .then((r) => setData(r.data))
      .catch((err) => {
        if (err.name !== "CanceledError") setError(err.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint, JSON.stringify(filters)]);

  return { data, loading, error };
}

export function useStudentPerformance(studentId: number | null) {
  const [data, setData] = useState<StudentPerformance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!studentId) return;
    setLoading(true);
    api
      .get(`/students/${studentId}/performance`)
      .then((r) => setData(r.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [studentId]);

  return { data, loading, error };
}

export interface StudentPerformance {
  student_id: number;
  full_name: string;
  roll_no: string;
  department: string;
  semester: number;
  attendance_pct: number;
  avg_marks_pct: number;
  assignment_completion_rate: number;
  lms_engagement_score: number;
  latest_prediction: {
    risk_label: string;
    risk_score: number;
    contributing_factors: { feature: string; impact: number; value: number }[];
    predicted_at: string;
  } | null;
}
