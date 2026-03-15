"""
Admin utility endpoints.

POST /admin/seed   — Seeds the database with default users, courses, and students.
                     Safe to call multiple times (idempotent).
                     ADMIN-only (production) or open once on a fresh database.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.user import User, Role
from app.models.student import Student
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/seed", status_code=200)
async def seed_database(db: AsyncSession = Depends(get_db)):
    """
    Seed the database with default users, courses, and students.
    Idempotent — skips records that already exist.
    Call this once after initial deployment via:
        POST /api/v1/admin/seed
    """
    result = {"created": {}, "skipped": {}}

    # ── Admin user ────────────────────────────────────────────────────────────
    existing_admin = (await db.execute(
        select(User).where(User.email == "admin@edusentinel.dev")
    )).scalar_one_or_none()

    if existing_admin:
        result["skipped"]["admin"] = "admin@edusentinel.dev"
        admin = existing_admin
    else:
        admin = User(
            email="admin@edusentinel.dev",
            full_name="System Admin",
            hashed_password=hash_password("Admin@123"),
            role=Role.ADMIN,
            department="Administration",
        )
        db.add(admin)
        await db.flush()
        result["created"]["admin"] = "admin@edusentinel.dev"

    # ── Faculty user ──────────────────────────────────────────────────────────
    existing_faculty = (await db.execute(
        select(User).where(User.email == "faculty@edusentinel.dev")
    )).scalar_one_or_none()

    if existing_faculty:
        result["skipped"]["faculty"] = "faculty@edusentinel.dev"
        faculty = existing_faculty
    else:
        faculty = User(
            email="faculty@edusentinel.dev",
            full_name="Dr. Priya Sharma",
            hashed_password=hash_password("Faculty@123"),
            role=Role.FACULTY,
            department="Computer Science",
        )
        db.add(faculty)
        await db.flush()
        result["created"]["faculty"] = "faculty@edusentinel.dev"

    # ── Courses ───────────────────────────────────────────────────────────────
    course_data = [
        ("CS501", "Data Structures", 5, 4),
        ("CS502", "Operating Systems", 5, 4),
        ("CS503", "Database Systems", 5, 3),
    ]
    courses = []
    created_courses = 0
    for code, name, semester, credits in course_data:
        existing = (await db.execute(
            select(Course).where(Course.code == code)
        )).scalar_one_or_none()
        if existing:
            courses.append(existing)
        else:
            c = Course(
                code=code, name=name, department="Computer Science",
                semester=semester, credits=credits,
                academic_year="2024-25", faculty_id=faculty.id,
            )
            db.add(c)
            courses.append(c)
            created_courses += 1
    await db.flush()
    result["created"]["courses"] = created_courses
    result["skipped"]["courses"] = len(course_data) - created_courses

    # ── Students ──────────────────────────────────────────────────────────────
    students = []
    created_students = 0
    for i in range(1, 21):
        roll = f"CS2021{str(i).zfill(3)}"
        existing = (await db.execute(
            select(Student).where(Student.roll_no == roll)
        )).scalar_one_or_none()
        if existing:
            students.append(existing)
        else:
            s = Student(
                roll_no=roll,
                full_name=f"Student {i}",
                email=f"student{i}@test.edu",
                department="Computer Science",
                semester=5,
                batch_year=2021,
            )
            db.add(s)
            students.append(s)
            created_students += 1
    await db.flush()
    result["created"]["students"] = created_students
    result["skipped"]["students"] = 20 - created_students

    # ── Enrollments ───────────────────────────────────────────────────────────
    existing_enrollments = set(
        (row.student_id, row.course_id)
        for row in (await db.execute(select(Enrollment))).scalars().all()
    )
    new_enrollments = 0
    for s in students:
        for c in courses:
            if (s.id, c.id) not in existing_enrollments:
                db.add(Enrollment(student_id=s.id, course_id=c.id))
                new_enrollments += 1

    await db.commit()
    result["created"]["enrollments"] = new_enrollments

    return {
        "message": "Seed complete",
        "details": result,
        "credentials": {
            "admin": {"email": "admin@edusentinel.dev", "password": "Admin@123"},
            "faculty": {"email": "faculty@edusentinel.dev", "password": "Faculty@123"},
        },
    }
