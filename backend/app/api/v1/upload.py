"""
Unified upload router — POST /upload/student-data

Accepts a CSV file with combined student metrics, auto-creates students,
stores data, runs ML predictions, and returns a summary.

Also provides typed endpoints for individual data types:
  POST /upload/attendance   — attendance CSV
  POST /upload/marks        — marks / academic CSV
  POST /upload/assignments  — assignment scores CSV
  POST /upload/lms          — LMS activity CSV
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.dependencies import get_db, get_current_user, require_role
from app.models.course import Course
from app.models.student import Student
from app.models.user import Role, User
from app.services import data_ingestion_service

router = APIRouter(prefix="/upload", tags=["Upload"])

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_csv(file: UploadFile) -> None:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationError("Only .csv files are accepted")


async def _read_limited(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise ValidationError("File exceeds 10 MB limit")
    return content


async def _get_lookups(db: AsyncSession) -> tuple[dict, dict]:
    students = (await db.execute(select(Student.roll_no, Student.id))).all()
    courses  = (await db.execute(select(Course.code,    Course.id))).all()
    return (
        {s.roll_no: s.id for s in students},
        {c.code:   c.id  for c in courses},
    )


# ── Unified student-data CSV ─────────────────────────────────────────────────

@router.post(
    "/student-data",
    summary="Upload unified student-data CSV (auto-creates students + predictions)",
)
async def upload_student_data(
    file: UploadFile = File(..., description=(
        "CSV with columns: student_name, roll_no, attendance (%), "
        "internal_score, assignment_score, lms_activity (0-100), "
        "engagement_time (hours), previous_gpa"
    )),
    semester: str = Form(
        default=...,
        description="Semester identifier, e.g. '2025-ODD'",
    ),
    department: str = Form(default="General"),
    batch_year: Optional[int] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """
    Parse a unified student performance CSV and:
    1. Auto-create student records for unknown roll numbers.
    2. Compute risk predictions (ML service or heuristic fallback).
    3. Persist Prediction records and HIGH-risk Alerts.

    Returns a summary with counts of students created, predictions generated,
    and any row-level errors.
    """
    _validate_csv(file)
    content = await _read_limited(file)

    result = await data_ingestion_service.ingest_student_data_csv(
        db=db,
        csv_bytes=content,
        recorded_by=current_user.id,
        semester=semester,
        department=department,
        batch_year=batch_year or datetime.now().year,
    )
    return result


# ── Attendance CSV ────────────────────────────────────────────────────────────

@router.post(
    "/attendance",
    summary="Upload attendance CSV",
)
async def upload_attendance(
    file: UploadFile = File(..., description="CSV: roll_no, course_code, date (YYYY-MM-DD), status (P/A/L)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Upload attendance records from CSV. Upserts on (student, course, date)."""
    _validate_csv(file)
    content = await _read_limited(file)
    student_lookup, course_lookup = await _get_lookups(db)

    return await data_ingestion_service.bulk_insert_attendance(
        db=db,
        csv_bytes=content,
        student_lookup=student_lookup,
        course_lookup=course_lookup,
        recorded_by=current_user.id,
    )


# ── Marks / Academic CSV ──────────────────────────────────────────────────────

@router.post(
    "/marks",
    summary="Upload marks / academic records CSV",
)
async def upload_marks(
    file: UploadFile = File(..., description=(
        "CSV: roll_no, course_code, exam_type (IA1/IA2/IA3/MIDTERM/FINAL/QUIZ/PRACTICAL), "
        "score, max_score, exam_date (YYYY-MM-DD)"
    )),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Upload internal assessment / exam marks from CSV."""
    _validate_csv(file)
    content = await _read_limited(file)
    student_lookup, course_lookup = await _get_lookups(db)

    return await data_ingestion_service.bulk_insert_academic(
        db=db,
        csv_bytes=content,
        student_lookup=student_lookup,
        course_lookup=course_lookup,
        recorded_by=current_user.id,
    )


# ── Assignments CSV ───────────────────────────────────────────────────────────

@router.post(
    "/assignments",
    summary="Upload assignment scores CSV",
)
async def upload_assignments(
    file: UploadFile = File(..., description=(
        "CSV: roll_no, course_code, title, score, max_score, is_submitted (true/false)"
    )),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Upload assignment submissions and scores from CSV."""
    _validate_csv(file)
    content = await _read_limited(file)
    student_lookup, course_lookup = await _get_lookups(db)

    return await data_ingestion_service.bulk_insert_assignments(
        db=db,
        csv_bytes=content,
        student_lookup=student_lookup,
        course_lookup=course_lookup,
        recorded_by=current_user.id,
    )


# ── LMS Activity CSV ──────────────────────────────────────────────────────────

@router.post(
    "/lms",
    summary="Upload LMS activity CSV",
)
async def upload_lms(
    file: UploadFile = File(..., description=(
        "CSV: roll_no, date (YYYY-MM-DD), login_count, content_views, "
        "quiz_attempts, forum_posts, time_spent_minutes"
    )),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Upload daily LMS engagement metrics from CSV. Upserts on (student, date)."""
    _validate_csv(file)
    content = await _read_limited(file)
    students = (await db.execute(select(Student.roll_no, Student.id))).all()
    student_lookup = {s.roll_no: s.id for s in students}

    return await data_ingestion_service.bulk_insert_lms(
        db=db,
        csv_bytes=content,
        student_lookup=student_lookup,
        recorded_by=current_user.id,
    )
