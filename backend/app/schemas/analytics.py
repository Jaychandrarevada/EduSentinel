"""Analytics / dashboard schemas."""
from pydantic import BaseModel


class CohortOverview(BaseModel):
    total_students: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    high_risk_pct: float
    avg_attendance_pct: float
    avg_marks_pct: float
    unresolved_alerts: int


class DepartmentStat(BaseModel):
    department: str
    total_students: int
    high_risk_count: int
    avg_attendance_pct: float
    avg_marks_pct: float


class AtRiskTrendPoint(BaseModel):
    week: str
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class CourseAnalytics(BaseModel):
    course_id: int
    course_name: str
    total_enrolled: int
    avg_attendance_pct: float
    avg_marks_pct: float
    assignment_completion_rate: float
    high_risk_count: int
