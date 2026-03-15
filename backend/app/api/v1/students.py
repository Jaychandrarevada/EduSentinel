"""
Students router — CRUD + performance summary.

RBAC
────
  GET    /students                Both roles. Faculty sees only their assigned students.
  POST   /students                ADMIN only.
  GET    /students/{id}           Both roles. Faculty restricted to their students.
  PUT    /students/{id}           ADMIN only.
  DELETE /students/{id}           ADMIN only.
  GET    /students/{id}/performance   Both roles. Faculty restricted to their students.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    assert_student_access,
    get_db,
    get_student_scope,
    require_role,
)
from app.models.user import Role, User
from app.schemas.common import PaginatedResponse
from app.schemas.student import (
    StudentCreate,
    StudentOut,
    StudentPerformanceSummary,
    StudentUpdate,
)
from app.services import student_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("", response_model=PaginatedResponse[StudentOut])
async def list_students(
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=12),
    search: Optional[str] = Query(None, max_length=100),
    risk_label: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    List students. Admins see all; faculty see only their assigned students.
    Supports department, semester, name search, and risk-label filters.
    """
    student_ids = list(scope) if scope is not None else None

    students, total = await student_service.list_students(
        db,
        department=department,
        semester=semester,
        search=search,
        risk_label=risk_label,
        page=page,
        size=size,
        student_ids=student_ids,
    )
    return PaginatedResponse.build(
        items=[StudentOut.model_validate(s) for s in students],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Register a new student. Admin only."""
    return await student_service.create_student(db, payload)


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """Get a student by ID. Faculty can only access their assigned students."""
    assert_student_access(student_id, scope)
    student = await student_service.get_student_or_404(db, student_id)
    return StudentOut.model_validate(student)


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Update student details. Admin only."""
    return await student_service.update_student(db, student_id, payload)


@router.delete("/{student_id}", status_code=204)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Delete a student and all associated records. Admin only."""
    await student_service.delete_student(db, student_id)


@router.get("/{student_id}/performance", response_model=StudentPerformanceSummary)
async def get_student_performance(
    student_id: int,
    semester: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Return a full performance snapshot: attendance, marks, assignments, LMS, and
    latest risk prediction.
    Faculty can only access students in their courses.
    """
    assert_student_access(student_id, scope)
    return await student_service.get_performance_summary(db, student_id, semester)
