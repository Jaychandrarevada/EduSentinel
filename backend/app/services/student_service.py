"""
Student service — full CRUD and performance aggregation queries.
"""
from typing import Optional
import structlog
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.student import Student
from app.models.attendance import Attendance, AttendanceStatus
from app.models.academic_record import AcademicRecord
from app.models.assignment import Assignment
from app.models.lms_activity import LMSActivity
from app.models.prediction import Prediction
from app.schemas.student import StudentCreate, StudentUpdate, StudentOut, StudentPerformanceSummary

log = structlog.get_logger()


async def list_students(
    db: AsyncSession,
    department: Optional[str] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None,
    risk_label: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    student_ids: Optional[list[int]] = None,
) -> tuple[list[Student], int]:
    q = select(Student)

    # Faculty data scope — restrict to assigned student IDs
    if student_ids is not None:
        q = q.where(Student.id.in_(student_ids))

    if department:
        q = q.where(Student.department == department)
    if semester:
        q = q.where(Student.semester == semester)
    if search:
        pattern = f"%{search.lower()}%"
        from sqlalchemy import or_
        q = q.where(
            or_(
                func.lower(Student.full_name).like(pattern),
                func.lower(Student.roll_no).like(pattern),
            )
        )

    # Filter by risk if requested (requires join with predictions)
    if risk_label:
        sub = (
            select(Prediction.student_id)
            .where(Prediction.risk_label == risk_label.upper())
            .distinct()
        )
        q = q.where(Student.id.in_(sub))

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar_one()
    students = (
        await db.execute(q.offset((page - 1) * size).limit(size))
    ).scalars().all()
    return list(students), total


async def get_student_or_404(db: AsyncSession, student_id: int) -> Student:
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise NotFoundError("Student", student_id)
    return student


async def create_student(db: AsyncSession, payload: StudentCreate) -> StudentOut:
    # Check for duplicates
    existing = await db.execute(
        select(Student).where(
            (Student.roll_no == payload.roll_no) | (Student.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Student with this roll number or email already exists")

    student = Student(**payload.model_dump())
    db.add(student)
    await db.flush()
    await db.refresh(student)
    await db.commit()
    log.info("student.created", student_id=student.id, roll_no=student.roll_no)
    return StudentOut.model_validate(student)


async def update_student(
    db: AsyncSession, student_id: int, payload: StudentUpdate
) -> StudentOut:
    student = await get_student_or_404(db, student_id)
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    await db.flush()
    await db.refresh(student)
    await db.commit()
    return StudentOut.model_validate(student)


async def delete_student(db: AsyncSession, student_id: int) -> None:
    student = await get_student_or_404(db, student_id)
    await db.delete(student)
    await db.commit()


async def get_performance_summary(
    db: AsyncSession, student_id: int, semester: Optional[str] = None
) -> StudentPerformanceSummary:
    student = await get_student_or_404(db, student_id)

    # ── Attendance ────────────────────────────
    att_q = select(
        func.count(Attendance.id).label("total"),
        func.count(Attendance.id).filter(
            Attendance.status == AttendanceStatus.PRESENT
        ).label("present"),
    ).where(Attendance.student_id == student_id)
    att = (await db.execute(att_q)).one()
    attendance_pct = (att.present / att.total * 100) if att.total else 0.0

    # ── Marks ─────────────────────────────────
    marks_q = select(
        func.avg(AcademicRecord.score / AcademicRecord.max_score * 100)
    ).where(AcademicRecord.student_id == student_id)
    avg_marks = (await db.execute(marks_q)).scalar_one() or 0.0

    # ── Assignments ───────────────────────────
    asgn_q = select(
        func.count(Assignment.id).label("total"),
        func.count(Assignment.id).filter(Assignment.is_submitted == True).label("submitted"),
    ).where(Assignment.student_id == student_id)
    asgn = (await db.execute(asgn_q)).one()
    completion_rate = (asgn.submitted / asgn.total * 100) if asgn.total else 0.0

    # ── LMS engagement ────────────────────────
    lms_q = select(
        func.avg(LMSActivity.login_count),
        func.avg(LMSActivity.content_views),
    ).where(LMSActivity.student_id == student_id)
    lms = (await db.execute(lms_q)).one()
    avg_logins = lms[0] or 0.0
    avg_views = lms[1] or 0.0
    engagement_score = min(100.0, (avg_logins / 5 * 50) + (avg_views / 10 * 50))

    # ── Latest prediction ─────────────────────
    pred_q = (
        select(Prediction)
        .where(Prediction.student_id == student_id)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    pred = (await db.execute(pred_q)).scalar_one_or_none()

    return StudentPerformanceSummary(
        student_id=student.id,
        roll_no=student.roll_no,
        full_name=student.full_name,
        department=student.department,
        semester=student.semester,
        attendance_pct=round(attendance_pct, 2),
        avg_marks_pct=round(float(avg_marks), 2),
        assignment_completion_rate=round(completion_rate, 2),
        lms_engagement_score=round(engagement_score, 2),
        risk_label=pred.risk_label if pred else None,
        risk_score=pred.risk_score if pred else None,
    )
