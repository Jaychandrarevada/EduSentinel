"""
Analytics service — cohort, department, course-level aggregate queries
for admin/faculty dashboards.
"""
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.attendance import Attendance, AttendanceStatus
from app.models.academic_record import AcademicRecord
from app.models.prediction import Prediction, RiskLabel
from app.models.student import Student
from app.schemas.analytics import (
    CohortOverview,
    DepartmentStat,
    CourseAnalytics,
)


async def get_cohort_overview(
    db: AsyncSession, semester: Optional[str] = None
) -> CohortOverview:
    # Risk counts from predictions
    pred_q = select(Prediction.risk_label, func.count().label("cnt"))
    if semester:
        pred_q = pred_q.where(Prediction.semester == semester)
    pred_q = pred_q.group_by(Prediction.risk_label)
    rows = (await db.execute(pred_q)).all()
    risk_counts = {r.risk_label: r.cnt for r in rows}

    total_students = (await db.execute(select(func.count(Student.id)))).scalar_one()

    avg_att = (await db.execute(
        select(func.avg(
            func.count(Attendance.id).filter(Attendance.status == AttendanceStatus.PRESENT)
            / func.count(Attendance.id) * 100
        ))
    )).scalar_one() or 0.0

    avg_marks = (await db.execute(
        select(func.avg(AcademicRecord.score / AcademicRecord.max_score * 100))
    )).scalar_one() or 0.0

    unresolved_alerts = (await db.execute(
        select(func.count(Alert.id)).where(Alert.is_resolved == False)
    )).scalar_one()

    high = risk_counts.get(RiskLabel.HIGH, 0)
    return CohortOverview(
        total_students=total_students,
        high_risk_count=high,
        medium_risk_count=risk_counts.get(RiskLabel.MEDIUM, 0),
        low_risk_count=risk_counts.get(RiskLabel.LOW, 0),
        high_risk_pct=round((high / total_students * 100) if total_students else 0, 1),
        avg_attendance_pct=round(float(avg_att), 2),
        avg_marks_pct=round(float(avg_marks), 2),
        unresolved_alerts=unresolved_alerts,
    )


async def get_department_stats(db: AsyncSession) -> list[DepartmentStat]:
    """Per-department aggregation of attendance, marks, and risk counts."""
    rows = (await db.execute(
        select(
            Student.department,
            func.count(Student.id).label("total"),
            func.count(Prediction.id).filter(Prediction.risk_label == RiskLabel.HIGH).label("high_risk"),
        )
        .outerjoin(Prediction, Prediction.student_id == Student.id)
        .group_by(Student.department)
        .order_by(Student.department)
    )).all()

    stats = []
    for row in rows:
        att_q = select(
            func.avg(
                func.count(Attendance.id).filter(Attendance.status == AttendanceStatus.PRESENT) * 100.0
                / func.nullif(func.count(Attendance.id), 0)
            )
        ).join(Student, Student.id == Attendance.student_id).where(
            Student.department == row.department
        )
        avg_att = (await db.execute(att_q)).scalar_one() or 0.0

        marks_q = select(
            func.avg(AcademicRecord.score / AcademicRecord.max_score * 100)
        ).join(Student, Student.id == AcademicRecord.student_id).where(
            Student.department == row.department
        )
        avg_marks = (await db.execute(marks_q)).scalar_one() or 0.0

        stats.append(DepartmentStat(
            department=row.department,
            total_students=row.total,
            high_risk_count=row.high_risk or 0,
            avg_attendance_pct=round(float(avg_att), 2),
            avg_marks_pct=round(float(avg_marks), 2),
        ))
    return stats
