"""
Academic records router — marks ingestion, CSV upload, and summaries.

RBAC
────
  POST /academic/marks            ADMIN or FACULTY.
  POST /academic/marks/bulk       ADMIN or FACULTY.
  POST /academic/marks/upload     ADMIN or FACULTY.
  GET  /academic/marks/summary/{id}  Both roles; faculty restricted to their students.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import assert_student_access, get_db, get_student_scope, require_role
from app.models.course import Course
from app.models.student import Student
from app.models.user import Role, User
from app.schemas.academic import (
    AcademicRecordBulkCreate,
    AcademicRecordCreate,
    AcademicRecordOut,
    AcademicSummary,
)
from app.schemas.attendance import BulkUploadResult
from app.core.exceptions import ValidationError
from app.services import academic_service

router = APIRouter(prefix="/academic", tags=["Academic Records"])


@router.post("/marks", response_model=AcademicRecordOut, status_code=201)
async def add_mark(
    payload: AcademicRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Add a single academic record (mark) for a student. Admin or Faculty."""
    return await academic_service.add_record(db, payload, recorded_by=current_user.id)


@router.post("/marks/bulk", response_model=BulkUploadResult)
async def bulk_add_marks(
    payload: AcademicRecordBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Bulk insert academic records (JSON body, max 500). Admin or Faculty."""
    return await academic_service.bulk_add_records(db, payload, recorded_by=current_user.id)


@router.post("/marks/upload", response_model=BulkUploadResult)
async def upload_marks_csv(
    file: UploadFile = File(..., description="CSV: roll_no,course_code,exam_type,score,max_score,exam_date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """
    Upload a CSV file of marks. Admin or Faculty.
    Required columns: roll_no, course_code, exam_type, score, max_score, exam_date
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise ValidationError("Only .csv files are accepted")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise ValidationError("File exceeds 10 MB limit")

    students = (await db.execute(select(Student.roll_no, Student.id))).all()
    courses = (await db.execute(select(Course.code, Course.id))).all()

    return await academic_service.ingest_csv(
        db,
        csv_bytes=content,
        student_lookup={s.roll_no: s.id for s in students},
        course_lookup={c.code: c.id for c in courses},
        recorded_by=current_user.id,
    )


@router.get("/marks/summary/{student_id}", response_model=AcademicSummary)
async def get_marks_summary(
    student_id: int,
    course_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Return aggregated mark statistics for a student.
    Faculty can only access their assigned students.
    """
    assert_student_access(student_id, scope)
    return await academic_service.get_summary(db, student_id, course_id)
