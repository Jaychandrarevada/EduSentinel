"""Faculty schemas — used by the admin faculty-management endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class FacultyOut(BaseModel):
    """Full faculty profile returned to the admin."""
    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    full_name: str
    department: Optional[str]
    is_active: bool
    created_at: datetime


class FacultyWithStats(FacultyOut):
    """Faculty profile enriched with course / student / alert counts."""
    course_count: int = 0
    student_count: int = 0
    unresolved_alert_count: int = 0


class FacultyUpdate(BaseModel):
    """
    Partial update payload for a faculty profile.
    All fields are optional — only provided fields are applied.
    """
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(default=None, max_length=100)


class FacultyActivateRequest(BaseModel):
    """Body for activate / deactivate endpoints."""
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason, stored in audit log.",
    )
