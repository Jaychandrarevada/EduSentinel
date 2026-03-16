"""Data generator router — POST /students/generate"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.alert import Alert
from app.models.academic_record import AcademicRecord
from app.models.assignment import Assignment
from app.models.attendance import Attendance
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lms_activity import LMSActivity
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import Role, User
from app.utils.data_generator import generate_and_insert_students

router = APIRouter(prefix="/students", tags=["Data Generation"])


class GenerateStudentsRequest(BaseModel):
    num_students: int = Field(ge=300, le=2000, examples=[500])
    semester: str = Field(default="2025-ODD", min_length=3, max_length=20)


class GenerateStudentsResponse(BaseModel):
    students_created: int
    semester: str
    high_risk: int
    medium_risk: int
    low_risk: int
    message: str


@router.post(
    "/generate",
    response_model=GenerateStudentsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate synthetic student data",
)
async def generate_students(
    payload: GenerateStudentsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    Generate between 300 and 2000 synthetic students with realistic academic
    distributions and insert them into the database.
    """
    try:
        result = await generate_and_insert_students(
            db, payload.num_students, payload.semester
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data generation failed: {exc}",
        )
    return GenerateStudentsResponse(
        **result,
        message=f"Successfully generated {result['students_created']} students for {payload.semester}.",
    )


@router.post(
    "/enroll-all",
    status_code=status.HTTP_200_OK,
    summary="Enroll all students into all courses (dev fix-up)",
    tags=["Data Generation"],
)
async def enroll_all_students(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """
    One-time fix: creates Enrollment rows for every student × every course
    that don't already exist. Useful after running the seeder without enrollments.
    """
    students = (await db.execute(select(Student.id))).scalars().all()
    courses = (await db.execute(select(Course.id))).scalars().all()

    # Fetch existing enrollments to avoid duplicates
    existing = set(
        (r[0], r[1])
        for r in (
            await db.execute(select(Enrollment.student_id, Enrollment.course_id))
        ).all()
    )

    new_enrollments = [
        Enrollment(student_id=sid, course_id=cid)
        for sid in students
        for cid in courses
        if (sid, cid) not in existing
    ]

    if new_enrollments:
        db.add_all(new_enrollments)
        await db.commit()

    return {
        "students": len(students),
        "courses": len(courses),
        "enrollments_created": len(new_enrollments),
        "message": f"Created {len(new_enrollments)} new enrollment(s). Faculty dashboard will now show students.",
    }


# ── Reset / bulk-delete generated students ────────────────────────────────────


class ResetStudentsResponse(BaseModel):
    students_deleted: int
    message: str


async def _delete_students_by_ids(db: AsyncSession, student_ids: list[int]) -> int:
    """Delete all data for the given student IDs and return the number deleted."""
    if not student_ids:
        return 0
    id_set = student_ids  # already a list
    await db.execute(delete(Alert).where(Alert.student_id.in_(id_set)))
    await db.execute(delete(Prediction).where(Prediction.student_id.in_(id_set)))
    await db.execute(delete(LMSActivity).where(LMSActivity.student_id.in_(id_set)))
    await db.execute(delete(Assignment).where(Assignment.student_id.in_(id_set)))
    await db.execute(delete(AcademicRecord).where(AcademicRecord.student_id.in_(id_set)))
    await db.execute(delete(Attendance).where(Attendance.student_id.in_(id_set)))
    await db.execute(delete(Enrollment).where(Enrollment.student_id.in_(id_set)))
    await db.execute(delete(Student).where(Student.id.in_(id_set)))
    await db.commit()
    return len(student_ids)


@router.post("/reset", response_model=ResetStudentsResponse, status_code=200, summary="Bulk-delete generated students")
@router.delete("/reset", response_model=ResetStudentsResponse, status_code=200, summary="Bulk-delete generated students")
async def reset_students(
    mode: Literal["last_n", "keep_first_n", "generated_all"] = Query(..., description="Deletion mode"),
    count: Optional[int] = Query(None, ge=1, le=10000, description="Required for last_n and keep_first_n"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """
    Bulk-delete generated students and all their related data.
    Parameters are passed as query strings: ?mode=last_n&count=300

    Modes
    ─────
    last_n        Delete the most recently created `count` students.
    keep_first_n  Keep the oldest `count` students, delete the rest.
    generated_all Delete ALL students whose roll_no begins with 'GEN'.
    """
    if mode in ("last_n", "keep_first_n") and count is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="`count` is required for last_n and keep_first_n modes.",
        )

    if mode == "last_n":
        rows = (await db.execute(
            select(Student.id).order_by(Student.id.desc()).limit(count)
        )).scalars().all()

    elif mode == "keep_first_n":
        keep_ids = (await db.execute(
            select(Student.id).order_by(Student.id.asc()).limit(count)
        )).scalars().all()
        rows = (await db.execute(
            select(Student.id).where(Student.id.notin_(keep_ids))
        )).scalars().all()

    else:  # generated_all
        rows = (await db.execute(
            select(Student.id).where(Student.roll_no.like("GEN%"))
        )).scalars().all()

    deleted = await _delete_students_by_ids(db, list(rows))

    mode_label = {
        "last_n": f"last {count}",
        "keep_first_n": f"all except first {count}",
        "generated_all": "all generated (GEN prefix)",
    }[mode]

    return ResetStudentsResponse(
        students_deleted=deleted,
        message=f"Deleted {deleted} student(s) ({mode_label}) and all their related records.",
    )
