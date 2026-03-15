"""Student schemas."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class StudentCreate(BaseModel):
    roll_no: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    department: str = Field(min_length=2, max_length=100)
    semester: int = Field(ge=1, le=12)
    batch_year: int = Field(ge=2000, le=2100)


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    department: str | None = Field(default=None, max_length=100)
    semester: int | None = Field(default=None, ge=1, le=12)


class StudentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    roll_no: str
    full_name: str
    email: EmailStr
    phone: str | None
    department: str
    semester: int
    batch_year: int
    created_at: datetime


class StudentPerformanceSummary(BaseModel):
    student_id: int
    roll_no: str
    full_name: str
    department: str
    semester: int
    attendance_pct: float
    avg_marks_pct: float
    assignment_completion_rate: float
    lms_engagement_score: float
    risk_label: str | None
    risk_score: float | None
