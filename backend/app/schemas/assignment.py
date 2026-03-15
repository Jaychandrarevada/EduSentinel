"""Assignment schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    student_id: int
    course_id: int
    title: str = Field(min_length=1, max_length=255)
    due_date: datetime | None = None
    submitted_at: datetime | None = None
    score: float | None = Field(default=None, ge=0)
    max_score: float = Field(default=100.0, gt=0)
    is_late: bool = False
    is_submitted: bool = False
    feedback: str | None = Field(default=None, max_length=1000)


class AssignmentBulkCreate(BaseModel):
    records: List[AssignmentCreate] = Field(min_length=1, max_length=500)


class AssignmentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    student_id: int
    course_id: int
    title: str
    due_date: datetime | None
    submitted_at: datetime | None
    score: float | None
    max_score: float
    is_late: bool
    is_submitted: bool
    feedback: str | None
    created_at: datetime


class AssignmentSummary(BaseModel):
    student_id: int
    course_id: int | None
    total_assignments: int
    submitted: int
    not_submitted: int
    late_submissions: int
    completion_rate: float
    on_time_rate: float
    avg_score_pct: float | None
