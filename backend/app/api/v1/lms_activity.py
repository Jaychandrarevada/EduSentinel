"""
LMS activity router — interaction log ingestion and engagement analytics.

RBAC
────
  POST /lms-activity          ADMIN or FACULTY.
  POST /lms-activity/bulk     ADMIN or FACULTY.
  GET  /lms-activity/summary/{id}  Both roles; faculty restricted to their students.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import assert_student_access, get_db, get_student_scope, require_role
from app.models.user import Role, User
from app.schemas.attendance import BulkUploadResult
from app.schemas.lms_activity import (
    LMSActivityBulkCreate,
    LMSActivityCreate,
    LMSActivityOut,
    LMSActivitySummary,
)
from app.services import lms_service

router = APIRouter(prefix="/lms-activity", tags=["LMS Activity"])


@router.post("", response_model=LMSActivityOut, status_code=201)
async def log_activity(
    payload: LMSActivityCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Log or update daily LMS activity for a student (upsert). Admin or Faculty."""
    return await lms_service.upsert_activity(db, payload)


@router.post("/bulk", response_model=BulkUploadResult)
async def bulk_log_activity(
    payload: LMSActivityBulkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Bulk insert/update LMS activity records. Admin or Faculty."""
    return await lms_service.bulk_upsert(db, payload)


@router.get("/summary/{student_id}", response_model=LMSActivitySummary)
async def lms_summary(
    student_id: int,
    days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Return LMS engagement metrics for a student.
    Faculty can only access their assigned students.
    """
    assert_student_access(student_id, scope)
    return await lms_service.get_summary(db, student_id, days)
