"""LMS Activity schemas."""
from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field


class LMSActivityCreate(BaseModel):
    student_id: int
    date: date
    login_count: int = Field(ge=0, default=0)
    content_views: int = Field(ge=0, default=0)
    quiz_attempts: int = Field(ge=0, default=0)
    forum_posts: int = Field(ge=0, default=0)
    time_spent_minutes: float = Field(ge=0, default=0.0)
    last_login: datetime | None = None


class LMSActivityBulkCreate(BaseModel):
    records: List[LMSActivityCreate] = Field(min_length=1, max_length=500)


class LMSActivityOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    student_id: int
    date: date
    login_count: int
    content_views: int
    quiz_attempts: int
    forum_posts: int
    time_spent_minutes: float
    last_login: datetime | None
    updated_at: datetime


class LMSActivitySummary(BaseModel):
    student_id: int
    days_active: int
    avg_logins_per_week: float
    avg_content_views: float
    total_time_hours: float
    days_since_last_login: int | None
    engagement_score: float  # composite 0-100
