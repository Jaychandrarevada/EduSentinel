"""
Faculty service — admin management of faculty accounts + faculty self-service queries.

Responsibilities
────────────────
  list_faculty()              List all faculty users (paginated, optional search)
  get_faculty_or_404()        Fetch one faculty user or raise 404
  update_faculty()            Admin updates faculty profile / department
  set_faculty_active()        Admin activates or deactivates a faculty account
  get_faculty_courses()       Courses assigned to a faculty member
  get_faculty_student_ids()   Student IDs in a faculty member's courses (scoping)
  get_faculty_students()      Full student rows for a faculty member (paginated)
  get_faculty_students_summary() Students with per-student metrics (attendance, marks, risk)
  get_faculty_alerts()        Active at-risk alerts for a faculty member's students
  get_faculty_stats()         Summary counts for a faculty profile card
  get_faculty_dashboard()     Full dashboard: KPIs + risk dist + subject performance
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


# ── Faculty dashboard ─────────────────────────────────────────────────────────

async def get_faculty_dashboard(db: AsyncSession, faculty_id: int) -> dict:
    """
    Return KPI stats, risk distribution, and per-subject performance
    for the faculty dashboard summary cards and charts.
    """
    from sqlalchemy import case as sa_case
    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.academic_record import AcademicRecord
    from app.models.assignment import Assignment
    from app.models.prediction import Prediction, RiskLabel

    student_ids = await get_faculty_student_ids(db, faculty_id)
    courses = await get_faculty_courses(db, faculty_id)

    empty = {
        "stats": {
            "total_students": 0,
            "at_risk_count": 0,
            "avg_attendance_pct": 0.0,
            "avg_assignment_score": 0.0,
        },
        "risk_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "subject_performance": [],
    }
    if not student_ids:
        return empty

    # Risk distribution
    risk_rows = (await db.execute(
        select(Prediction.risk_label, func.count().label("cnt"))
        .where(Prediction.student_id.in_(student_ids))
        .group_by(Prediction.risk_label)
    )).all()
    risk_counts: dict = {r.risk_label: r.cnt for r in risk_rows}
    at_risk_count = (
        risk_counts.get(RiskLabel.HIGH, 0) + risk_counts.get(RiskLabel.MEDIUM, 0)
    )

    # Average attendance across all courses
    avg_att = (await db.execute(
        select(
            func.avg(sa_case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)) * 100
        ).where(Attendance.student_id.in_(student_ids))
    )).scalar_one() or 0.0

    # Average assignment score (submitted only)
    avg_assign = (await db.execute(
        select(func.avg(Assignment.score / Assignment.max_score * 100))
        .where(
            Assignment.student_id.in_(student_ids),
            Assignment.is_submitted == True,   # noqa: E712
            Assignment.max_score > 0,
        )
    )).scalar_one() or 0.0

    # Per-subject performance
    subject_perf = []
    for course in courses:
        c_att = (await db.execute(
            select(
                func.avg(sa_case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)) * 100
            ).where(
                Attendance.student_id.in_(student_ids),
                Attendance.course_id == course.id,
            )
        )).scalar_one() or 0.0

        c_marks = (await db.execute(
            select(func.avg(AcademicRecord.score / AcademicRecord.max_score * 100))
            .where(
                AcademicRecord.student_id.in_(student_ids),
                AcademicRecord.course_id == course.id,
                AcademicRecord.max_score > 0,
            )
        )).scalar_one() or 0.0

        # Students enrolled in this specific course
        c_student_ids = (await db.execute(
            select(Enrollment.student_id)
            .where(Enrollment.course_id == course.id)
        )).scalars().all()

        c_students = len(c_student_ids)

        # At-risk count (HIGH or MEDIUM) for students in this course
        c_at_risk = 0
        if c_student_ids:
            c_at_risk = (await db.execute(
                select(func.count(Prediction.student_id.distinct()))
                .where(
                    Prediction.student_id.in_(c_student_ids),
                    Prediction.risk_label.in_([RiskLabel.HIGH, RiskLabel.MEDIUM]),
                )
            )).scalar_one() or 0

        subject_perf.append({
            "course_id": course.id,
            "course_name": course.name,
            "course_code": course.code,
            "student_count": c_students,
            "at_risk_count": int(c_at_risk),
            "avg_attendance_pct": round(float(c_att), 1),
            "avg_marks_pct": round(float(c_marks), 1),
        })

    return {
        "stats": {
            "total_students": len(student_ids),
            "at_risk_count": at_risk_count,
            "avg_attendance_pct": round(float(avg_att), 1),
            "avg_assignment_score": round(float(avg_assign), 1),
        },
        "risk_distribution": {
            "HIGH": risk_counts.get(RiskLabel.HIGH, 0),
            "MEDIUM": risk_counts.get(RiskLabel.MEDIUM, 0),
            "LOW": risk_counts.get(RiskLabel.LOW, 0),
        },
        "subject_performance": subject_perf,
    }


async def get_faculty_students_summary(
    db: AsyncSession,
    faculty_id: int,
    search: Optional[str] = None,
    risk_label: Optional[str] = None,
    course_id: Optional[int] = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict], int]:
    """
    Return paginated students with per-student metrics:
    attendance %, marks %, assignment %, latest risk label + score.
    Optionally filter by a specific course_id.
    Used by the faculty All Students table.
    """
    from sqlalchemy import case as sa_case, or_
    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.academic_record import AcademicRecord
    from app.models.assignment import Assignment
    from app.models.prediction import Prediction

    # Base: students in faculty's courses (optionally filtered by course)
    base_q = (
        select(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )
    if course_id is not None:
        base_q = base_q.where(Course.id == course_id)
    if search:
        pattern = f"%{search.lower()}%"
        base_q = base_q.where(
            or_(
                func.lower(Student.full_name).like(pattern),
                func.lower(Student.roll_no).like(pattern),
            )
        )

    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    students = (await db.execute(
        base_q.order_by(Student.full_name).offset((page - 1) * size).limit(size)
    )).scalars().all()

    if not students:
        return [], total

    sids = [s.id for s in students]

    # Attendance per student
    att_rows = (await db.execute(
        select(
            Attendance.student_id,
            (func.avg(sa_case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)) * 100).label("att_pct"),
        )
        .where(Attendance.student_id.in_(sids))
        .group_by(Attendance.student_id)
    )).all()
    att_map = {r.student_id: round(float(r.att_pct), 1) for r in att_rows}

    # Marks per student
    marks_rows = (await db.execute(
        select(
            AcademicRecord.student_id,
            (func.avg(AcademicRecord.score / AcademicRecord.max_score * 100)).label("marks_pct"),
        )
        .where(AcademicRecord.student_id.in_(sids), AcademicRecord.max_score > 0)
        .group_by(AcademicRecord.student_id)
    )).all()
    marks_map = {r.student_id: round(float(r.marks_pct), 1) for r in marks_rows}

    # Assignment score per student
    assign_rows = (await db.execute(
        select(
            Assignment.student_id,
            (func.avg(Assignment.score / Assignment.max_score * 100)).label("assign_pct"),
        )
        .where(
            Assignment.student_id.in_(sids),
            Assignment.is_submitted == True,   # noqa: E712
            Assignment.max_score > 0,
        )
        .group_by(Assignment.student_id)
    )).all()
    assign_map = {r.student_id: round(float(r.assign_pct), 1) for r in assign_rows}

    # Latest prediction per student (most recent predicted_at)
    pred_rows = (await db.execute(
        select(Prediction)
        .where(Prediction.student_id.in_(sids))
        .order_by(Prediction.student_id, Prediction.predicted_at.desc())
        .distinct(Prediction.student_id)
    )).scalars().all()
    pred_map = {
        p.student_id: {
            "risk_label": p.risk_label.value if hasattr(p.risk_label, "value") else str(p.risk_label),
            "risk_score": round(p.risk_score, 3),
        }
        for p in pred_rows
    }

    result = []
    for s in students:
        pred = pred_map.get(s.id, {})
        if risk_label and pred.get("risk_label") != risk_label:
            continue
        result.append({
            "id": s.id,
            "roll_no": s.roll_no,
            "full_name": s.full_name,
            "department": s.department,
            "semester": s.semester,
            "attendance_pct": att_map.get(s.id, 0.0),
            "marks_pct": marks_map.get(s.id, 0.0),
            "assignment_pct": assign_map.get(s.id, 0.0),
            "risk_label": pred.get("risk_label"),
            "risk_score": pred.get("risk_score"),
        })

    return result, total
