"""Data generator router — POST /students/generate"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.course import Course
from app.models.enrollment import Enrollment
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
