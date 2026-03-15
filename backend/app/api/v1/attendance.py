"""
Attendance router — single entry, bulk JSON, CSV upload, summary.

RBAC
────
  POST   /attendance          ADMIN or FACULTY (record for their own courses).
  POST   /attendance/bulk     ADMIN or FACULTY.
  POST   /attendance/upload   ADMIN or FACULTY.
  GET    /attendance/summary/{id}  Both roles; faculty restricted to their students.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import assert_student_access, get_db, get_student_scope, require_role
from app.models.course import Course
from app.models.student import Student
from app.models.user import Role, User
from app.schemas.attendance import (
    AttendanceBulkCreate,
    AttendanceCreate,
    AttendanceOut,
    AttendanceSummary,
    BulkUploadResult,
)
from app.core.exceptions import ValidationError
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("", response_model=AttendanceOut, status_code=201)
async def add_attendance(
    payload: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Record a single attendance entry (upsert). Admin or Faculty."""
    return await attendance_service.add_single(db, payload, recorded_by=current_user.id)


@router.post("/bulk", response_model=BulkUploadResult)
async def bulk_attendance(
    payload: AttendanceBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Bulk insert/update attendance records (JSON body, max 1000). Admin or Faculty."""
    return await attendance_service.bulk_add(db, payload, recorded_by=current_user.id)


@router.post("/upload", response_model=BulkUploadResult)
async def upload_attendance_csv(
    file: UploadFile = File(..., description="CSV: roll_no,course_code,date,status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """
    Upload a CSV of attendance records. Admin or Faculty.
    Required columns: roll_no, course_code, date (YYYY-MM-DD), status (P/A/L)
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise ValidationError("Only .csv files are accepted")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise ValidationError("File exceeds 10 MB limit")

    students = (await db.execute(select(Student.roll_no, Student.id))).all()
    courses = (await db.execute(select(Course.code, Course.id))).all()

    return await attendance_service.ingest_csv(
        db,
        csv_bytes=content,
        student_lookup={s.roll_no: s.id for s in students},
        course_lookup={c.code: c.id for c in courses},
        recorded_by=current_user.id,
    )


@router.get("/summary/{student_id}", response_model=AttendanceSummary)
async def attendance_summary(
    student_id: int,
    course_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Return attendance aggregates for a student.
    Faculty can only access their assigned students.
    """
    assert_student_access(student_id, scope)
    return await attendance_service.get_summary(db, student_id, course_id)
