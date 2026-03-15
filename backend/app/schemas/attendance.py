"""Attendance schemas."""
from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field


class AttendanceCreate(BaseModel):
    student_id: int
    course_id: int
    date: date
    status: str = Field(pattern="^(P|A|L)$")


class AttendanceBulkCreate(BaseModel):
    records: List[AttendanceCreate] = Field(min_length=1, max_length=1000)


class AttendanceOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    student_id: int
    course_id: int
    date: date
    status: str
    created_at: datetime


class AttendanceSummary(BaseModel):
    student_id: int
    course_id: int | None
    total_classes: int
    present: int
    absent: int
    leave: int
    attendance_pct: float
    is_at_risk: bool  # True if pct < 75


class BulkUploadResult(BaseModel):
    inserted: int
    updated: int
    skipped: int
    errors: List[str]
