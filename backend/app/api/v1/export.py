"""
CSV export router — GET /export/student-data

Returns a downloadable CSV with student performance + risk prediction data.
Scoped by faculty role (only sees their enrolled students).
"""
import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_student_scope
from app.models.assignment import Assignment
from app.models.attendance import Attendance, AttendanceStatus  # AttendanceStatus.PRESENT = 'P'
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import User

router = APIRouter(prefix="/export", tags=["Export"])

CSV_HEADERS = [
    "student_id", "roll_no", "full_name", "email", "department",
    "semester", "batch_year", "risk_label", "risk_score",
    "attendance_pct", "assignment_avg", "predicted_at",
]


@router.get("/student-data", summary="Export student performance as CSV")
async def export_student_data(
    semester: Optional[str] = Query(None, description="Filter by semester, e.g. 2025-ODD"),
    risk_label: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Download student performance data as a CSV file.

    - Faculty: scoped to their enrolled students only.
    - Admin: returns all students.
    - Filters: semester and risk_label are optional.
    """
    # ── Fetch students ───────────────────────────────────────────────────────
    sq = select(Student)
    if scope is not None:
        sq = sq.where(Student.id.in_(list(scope)))
    students = (await db.execute(sq)).scalars().all()
    student_ids = [s.id for s in students]

    if not student_ids:
        # Return empty CSV with just headers
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_HEADERS)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=student_performance_empty.csv"},
        )

    # ── Latest prediction per student ────────────────────────────────────────
    pred_q = (
        select(
            Prediction.student_id,
            func.max(Prediction.predicted_at).label("latest_at"),
        )
        .where(Prediction.student_id.in_(student_ids))
        .group_by(Prediction.student_id)
        .subquery()
    )
    pred_full_q = select(Prediction).join(
        pred_q,
        (Prediction.student_id == pred_q.c.student_id)
        & (Prediction.predicted_at == pred_q.c.latest_at),
    )
    if semester:
        pred_full_q = pred_full_q.where(Prediction.semester == semester)
    if risk_label:
        pred_full_q = pred_full_q.where(Prediction.risk_label == risk_label.upper())

    predictions = (await db.execute(pred_full_q)).scalars().all()
    pred_map: dict[int, Prediction] = {p.student_id: p for p in predictions}

    # ── Attendance average per student ────────────────────────────────────────
    all_att = (await db.execute(
        select(Attendance.student_id, Attendance.status)
        .where(Attendance.student_id.in_(student_ids))
    )).all()

    att_map: dict[int, float] = {}
    att_totals: dict[int, list] = {}
    for row in all_att:
        att_totals.setdefault(row.student_id, []).append(row.status)
    for sid, statuses in att_totals.items():
        present = sum(1 for s in statuses if s == AttendanceStatus.PRESENT)
        att_map[sid] = round((present / len(statuses) * 100) if statuses else 0.0, 1)

    # ── Assignment average per student ────────────────────────────────────────
    all_asgn = (await db.execute(
        select(Assignment.student_id, Assignment.score, Assignment.max_score, Assignment.is_submitted)
        .where(Assignment.student_id.in_(student_ids))
    )).all()

    asgn_map: dict[int, float] = {}
    asgn_scores: dict[int, list] = {}
    for row in all_asgn:
        if row.is_submitted and row.score is not None and row.max_score and row.max_score > 0:
            asgn_scores.setdefault(row.student_id, []).append(row.score / row.max_score * 100)
    for sid, scores in asgn_scores.items():
        asgn_map[sid] = round(sum(scores) / len(scores), 1) if scores else 0.0

    # ── Build CSV ─────────────────────────────────────────────────────────────
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)

    # Apply risk_label filter to student list
    filtered_students = students
    if risk_label and pred_map:
        filtered_students = [s for s in students if pred_map.get(s.id) and pred_map[s.id].risk_label == risk_label.upper()]

    for student in filtered_students:
        pred = pred_map.get(student.id)
        writer.writerow([
            student.id,
            student.roll_no,
            student.full_name,
            student.email,
            student.department,
            student.semester,
            student.batch_year,
            pred.risk_label if pred else "N/A",
            round(pred.risk_score, 3) if pred else "N/A",
            att_map.get(student.id, "N/A"),
            asgn_map.get(student.id, "N/A"),
            pred.predicted_at.isoformat() if pred else "N/A",
        ])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"student_performance_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
