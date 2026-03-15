"""
Faculty service — admin management of faculty accounts + faculty self-service queries.

Responsibilities
────────────────
  list_faculty()            List all faculty users (paginated, optional search)
  get_faculty_or_404()      Fetch one faculty user or raise 404
  update_faculty()          Admin updates faculty profile / department
  set_faculty_active()      Admin activates or deactivates a faculty account
  get_faculty_courses()     Courses assigned to a faculty member
  get_faculty_student_ids() Student IDs in a faculty member's courses (scoping)
  get_faculty_students()    Full student rows for a faculty member (paginated)
  get_faculty_alerts()      Active at-risk alerts for a faculty member's students
  get_faculty_stats()       Summary counts for a faculty profile card
"""
from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.alert import Alert
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.user import Role, User
from app.schemas.faculty import FacultyUpdate

log = structlog.get_logger()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_faculty(user: User) -> None:
    """Raise PermissionDeniedError if user is not FACULTY."""
    if user.role != Role.FACULTY:
        raise PermissionDeniedError("User is not a faculty member")


# ── Admin: faculty management ─────────────────────────────────────────────────

async def list_faculty(
    db: AsyncSession,
    search: Optional[str] = None,
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[User], int]:
    """
    Return a paginated list of faculty users.
    Optionally filter by name/email search, department, or active status.
    """
    q = select(User).where(User.role == Role.FACULTY)

    if search:
        pattern = f"%{search.lower()}%"
        from sqlalchemy import or_
        q = q.where(
            or_(
                func.lower(User.full_name).like(pattern),
                func.lower(User.email).like(pattern),
            )
        )
    if department:
        q = q.where(User.department == department)
    if is_active is not None:
        q = q.where(User.is_active == is_active)

    q = q.order_by(User.full_name)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    users = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return list(users), total


async def get_faculty_or_404(db: AsyncSession, faculty_id: int) -> User:
    """Fetch a faculty user by ID or raise 404."""
    result = await db.execute(
        select(User).where(User.id == faculty_id, User.role == Role.FACULTY)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Faculty", faculty_id)
    return user


async def update_faculty(
    db: AsyncSession,
    faculty_id: int,
    payload: FacultyUpdate,
) -> User:
    """
    Admin updates a faculty member's profile.
    Only non-None fields in the payload are applied (partial update).
    """
    faculty = await get_faculty_or_404(db, faculty_id)

    if payload.full_name is not None:
        faculty.full_name = payload.full_name
    if payload.department is not None:
        faculty.department = payload.department
    if payload.email is not None:
        # Guard against email collision
        existing = await db.execute(
            select(User).where(User.email == payload.email, User.id != faculty_id)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Email '{payload.email}' is already in use")
        faculty.email = payload.email

    await db.flush()
    await db.refresh(faculty)
    log.info("faculty.updated", faculty_id=faculty_id)
    return faculty


async def set_faculty_active(
    db: AsyncSession,
    faculty_id: int,
    active: bool,
    requested_by: int,
) -> User:
    """Activate or deactivate a faculty account."""
    faculty = await get_faculty_or_404(db, faculty_id)

    if faculty.id == requested_by:
        raise PermissionDeniedError("Admins cannot deactivate their own account via this endpoint")

    faculty.is_active = active
    await db.flush()
    await db.refresh(faculty)
    action = "activated" if active else "deactivated"
    log.info(f"faculty.{action}", faculty_id=faculty_id, by=requested_by)
    return faculty


# ── Faculty: self-service queries ─────────────────────────────────────────────

async def get_faculty_student_ids(
    db: AsyncSession,
    faculty_id: int,
) -> list[int]:
    """
    Return IDs of all students enrolled in any course taught by `faculty_id`.
    Used by the dependency layer for data scoping.
    """
    result = await db.execute(
        select(Enrollment.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )
    return [row[0] for row in result.all()]


async def get_faculty_courses(
    db: AsyncSession,
    faculty_id: int,
) -> list[Course]:
    """Return all courses assigned to a faculty member."""
    result = await db.execute(
        select(Course)
        .where(Course.faculty_id == faculty_id)
        .order_by(Course.academic_year.desc(), Course.name)
    )
    return list(result.scalars().all())


async def get_faculty_students(
    db: AsyncSession,
    faculty_id: int,
    search: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[int] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Student], int]:
    """
    Return students enrolled in any of the faculty's courses.
    Supports name search, department, and semester filters.
    """
    q = (
        select(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )

    if search:
        pattern = f"%{search.lower()}%"
        from sqlalchemy import or_
        q = q.where(
            or_(
                func.lower(Student.full_name).like(pattern),
                func.lower(Student.roll_no).like(pattern),
            )
        )
    if department:
        q = q.where(Student.department == department)
    if semester:
        q = q.where(Student.semester == semester)

    q = q.order_by(Student.full_name)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    students = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return list(students), total


async def get_faculty_alerts(
    db: AsyncSession,
    faculty_id: int,
    is_resolved: bool = False,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Alert], int]:
    """
    Return alerts for students in the faculty's courses.
    Defaults to unresolved alerts only.
    """
    student_ids_q = (
        select(Enrollment.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )

    q = (
        select(Alert)
        .where(
            Alert.student_id.in_(student_ids_q),
            Alert.is_resolved == is_resolved,
        )
        .order_by(Alert.created_at.desc())
    )

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    alerts = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return list(alerts), total


async def get_faculty_stats(db: AsyncSession, faculty_id: int) -> dict:
    """
    Return a summary dict for a faculty profile card:
      course_count, student_count, unresolved_alert_count
    """
    course_count = (
        await db.execute(
            select(func.count(Course.id)).where(Course.faculty_id == faculty_id)
        )
    ).scalar_one()

    student_count_q = (
        select(func.count(Enrollment.student_id.distinct()))
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
    )
    student_count = (await db.execute(student_count_q)).scalar_one()

    student_ids_q = (
        select(Enrollment.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )
    alert_count = (
        await db.execute(
            select(func.count(Alert.id)).where(
                Alert.student_id.in_(student_ids_q),
                Alert.is_resolved == False,  # noqa: E712
            )
        )
    ).scalar_one()

    return {
        "course_count": course_count,
        "student_count": student_count,
        "unresolved_alert_count": alert_count,
    }
