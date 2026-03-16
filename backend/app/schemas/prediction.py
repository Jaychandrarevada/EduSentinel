"""Prediction and alert schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator


class RiskFactor(BaseModel):
    feature: str
    impact: float
    value: float


class PredictionOut(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    student_id: int
    semester: str
    risk_score: float
    risk_label: str
    contributing_factors: List[RiskFactor] | None
    model_version: str
    predicted_at: datetime


class PredictionRunRequest(BaseModel):
    semester: str = Field(min_length=3, max_length=20, examples=["2025-ODD"])
    force_retrain: bool = False


class PredictionRunResponse(BaseModel):
    message: str
    semester: str
    job_id: str | None = None


class AlertOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    student_id: int
    course_id: int | None
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    created_at: datetime


class AlertResolveRequest(BaseModel):
    resolution_note: str | None = Field(default=None, max_length=500)


# ── Quick risk prediction (simplified public-facing schema) ────────────────

class RiskPredictRequest(BaseModel):
    attendance: float = Field(
        ge=0.0, le=100.0,
        description="Attendance percentage (0–100)",
        examples=[75.0],
    )
    internal_score: float = Field(
        ge=0.0, le=100.0,
        description="Internal/IA assessment score (0–100)",
        examples=[68.0],
    )
    assignment_score: float = Field(
        ge=0.0, le=100.0,
        description="Average assignment score (0–100)",
        examples=[70.0],
    )
    lms_activity: float = Field(
        ge=0.0, le=100.0,
        description="LMS activity level as a percentage (0–100)",
        examples=[40.0],
    )
    engagement_time: float = Field(
        ge=0.0,
        description="Weekly LMS engagement time in hours",
        examples=[12.0],
    )
    previous_gpa: float = Field(
        ge=0.0, le=10.0,
        description="Previous semester GPA (0–10 scale)",
        examples=[6.5],
    )


class RiskPredictResponse(BaseModel):
    risk_level: str           # "High" | "Medium" | "Low"
    probability: float        # 0.0 – 1.0
    recommendation: str
