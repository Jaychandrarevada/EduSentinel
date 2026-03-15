"""Pydantic schemas for ML service request/response."""
from typing import Optional
from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    feature: str
    label: str
    impact: float
    value: float
    direction: str  # "increases_risk" | "decreases_risk"


class StudentPrediction(BaseModel):
    student_id: int
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_label: str  # "HIGH" | "MEDIUM" | "LOW"
    contributing_factors: list[RiskFactor]


class SinglePredictRequest(BaseModel):
    student_id: int
    attendance_pct: float = Field(ge=0.0, le=100.0)
    ia1_score: float = Field(ge=0.0, le=100.0)
    ia2_score: float = Field(ge=0.0, le=100.0)
    ia3_score: float = Field(ge=0.0, le=100.0)
    assignment_avg_score: float = Field(ge=0.0, le=100.0)
    assignment_completion_rate: float = Field(ge=0.0, le=1.0)
    lms_login_frequency: float = Field(ge=0.0)
    lms_time_spent_hours: float = Field(ge=0.0)
    lms_content_views: float = Field(ge=0.0)
    previous_gpa: float = Field(ge=0.0, le=10.0)


class BatchPredictRequest(BaseModel):
    semester: str
    lookback_weeks: int = Field(default=16, ge=4, le=52)


class BatchPredictResponse(BaseModel):
    semester: str
    predictions: list[StudentPrediction]
    total: int


class TrainRequest(BaseModel):
    data_source: str = Field(
        default="synthetic",
        description="One of: 'synthetic', 'csv'",
    )
    csv_path: Optional[str] = None
    n_synthetic_samples: int = Field(default=2000, ge=200, le=20000)


class TrainResponse(BaseModel):
    message: str
    version: Optional[str] = None
    model_name: Optional[str] = None
    metrics: Optional[dict] = None
    quality_gates_passed: Optional[bool] = None


class ModelInfoResponse(BaseModel):
    status: str
    version: Optional[str] = None
    model_name: Optional[str] = None
    threshold: Optional[float] = None
    metrics: Optional[dict] = None
    feature_cols: Optional[list[str]] = None
    created_at: Optional[str] = None
