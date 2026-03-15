"""Academic record schemas (marks)."""
from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field, field_validator


class AcademicRecordCreate(BaseModel):
    student_id: int
    course_id: int
    exam_type: str = Field(pattern="^(IA1|IA2|IA3|MIDTERM|FINAL|QUIZ|PRACTICAL)$")
    score: float = Field(ge=0)
    max_score: float = Field(gt=0, default=100.0)
    exam_date: date
    remarks: str | None = Field(default=None, max_length=500)

    @field_validator("score")
    @classmethod
    def score_within_max(cls, v: float, info) -> float:
        max_score = info.data.get("max_score", 100.0)
        if max_score and v > max_score:
            raise ValueError(f"score ({v}) cannot exceed max_score ({max_score})")
        return v


class AcademicRecordOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    student_id: int
    course_id: int
    exam_type: str
    score: float
    max_score: float
    percentage: float
    exam_date: date
    remarks: str | None
    created_at: datetime


class AcademicRecordBulkCreate(BaseModel):
    records: List[AcademicRecordCreate] = Field(min_length=1, max_length=500)


class AcademicSummary(BaseModel):
    student_id: int
    course_id: int | None
    exam_counts: dict  # {exam_type: count}
    avg_percentage: float
    highest_score_pct: float
    lowest_score_pct: float
    trend: str  # "improving" | "declining" | "stable"
