// ─────────────────────────────────────────────
//  Shared TypeScript types for EduSentinel
// ─────────────────────────────────────────────

// ── Auth ──────────────────────────────────────
export type Role = "ADMIN" | "FACULTY";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  token_type: "bearer";
}

// ── Student ───────────────────────────────────
export interface Student {
  id: number;
  roll_no: string;
  full_name: string;
  department: string;
  semester: number;
  batch_year: number;
  email: string;
  phone?: string;
}

// ── Risk / Prediction ─────────────────────────
export type RiskLabel = "LOW" | "MEDIUM" | "HIGH";

export interface RiskFactor {
  feature: string;
  impact: number;   // SHAP value magnitude
  value: number;    // actual feature value
}

export interface Prediction {
  student_id: number;
  student_name: string;
  risk_score: number;           // 0.0 – 1.0
  risk_label: RiskLabel;
  contributing_factors: RiskFactor[];
  model_version: string;
  predicted_at: string;         // ISO datetime
}

// ── Alert ─────────────────────────────────────
export type AlertSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Alert {
  id: number;
  student_id: number;
  student_name: string;
  course_id: number;
  course_name: string;
  alert_type: string;
  severity: AlertSeverity;
  message: string;
  is_resolved: boolean;
  created_at: string;
}

// ── Analytics ─────────────────────────────────
export interface CohortSummary {
  total_students: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  avg_attendance_pct: number;
  avg_marks_pct: number;
  unresolved_alerts?: number;
}

export interface TrendPoint {
  week: string;
  value: number;
}

// ── API Helpers ───────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// ── ML Model Evaluation ───────────────────────
export interface ModelMetrics {
  name: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  training_time_sec?: number;
}

export interface ModelComparisonResult {
  models: ModelMetrics[];
  best_model: string;
  best_metric: string;
  comparison_date: string;
  data_source: string;
}

// ── SHAP / Explainability ─────────────────────
export interface FeatureImportance {
  feature: string;
  importance: number;
  description: string;
}

export interface GlobalShapResult {
  feature_importance: FeatureImportance[];
  model_name: string;
  data_source: string;
}

export interface ShapExplanationEntry {
  feature: string;
  value: number;
  shap_value: number;
  direction: "increases_risk" | "decreases_risk";
}

export interface StudentShapResult {
  student_id: number;
  risk_score: number;
  risk_label: RiskLabel;
  explanation: ShapExplanationEntry[];
}

// ── Data Generator ────────────────────────────
export interface GenerateStudentsRequest {
  num_students: number;
  semester: string;
}

export interface GenerateStudentsResponse {
  students_created: number;
  semester: string;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  message: string;
}
