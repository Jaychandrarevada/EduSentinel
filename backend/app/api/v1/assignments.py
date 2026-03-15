"""
Assignment router — submission tracking and analytics.

RBAC
────
  POST /assignments           ADMIN or FACULTY.
  POST /assignments/bulk      ADMIN or FACULTY.
  GET  /assignments/summary/{id}  Both roles; faculty restricted to their students.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import assert_student_access, get_db, get_student_scope, require_role
from app.models.user import Role, User
from app.schemas.assignment import (
    AssignmentBulkCreate,
    AssignmentCreate,
    AssignmentOut,
    AssignmentSummary,
)
from app.schemas.attendance import BulkUploadResult
from app.services import assignment_service

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.post("", response_model=AssignmentOut, status_code=201)
async def add_assignment(
    payload: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Add a single assignment submission record. Admin or Faculty."""
    return await assignment_service.add_assignment(db, payload, recorded_by=current_user.id)


@router.post("/bulk", response_model=BulkUploadResult)
async def bulk_assignments(
    payload: AssignmentBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Bulk insert assignment records (JSON, max 500). Admin or Faculty."""
    return await assignment_service.bulk_add(db, payload, recorded_by=current_user.id)


@router.get("/summary/{student_id}", response_model=AssignmentSummary)
async def assignment_summary(
    student_id: int,
    course_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Return assignment completion and scoring analytics for a student.
    Faculty can only access their assigned students.
    """
    assert_student_access(student_id, scope)
    return await assignment_service.get_summary(db, student_id, course_id)
