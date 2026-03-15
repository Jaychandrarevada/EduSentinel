"""Assignment service — ingestion and summary analytics."""
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentBulkCreate,
    AssignmentOut,
    AssignmentSummary,
)
from app.schemas.attendance import BulkUploadResult

log = structlog.get_logger()


async def add_assignment(
    db: AsyncSession, payload: AssignmentCreate, recorded_by: int
) -> AssignmentOut:
    record = Assignment(**payload.model_dump(), recorded_by=recorded_by)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    await db.commit()
    return AssignmentOut.model_validate(record)


async def bulk_add(
    db: AsyncSession, payload: AssignmentBulkCreate, recorded_by: int
) -> BulkUploadResult:
    inserted, errors = 0, []
    for i, rec in enumerate(payload.records):
        try:
            db.add(Assignment(**rec.model_dump(), recorded_by=recorded_by))
            inserted += 1
        except Exception as exc:
            errors.append(f"Row {i + 1}: {exc}")
    await db.commit()
    return BulkUploadResult(inserted=inserted, updated=0, skipped=len(errors), errors=errors)


async def get_summary(
    db: AsyncSession, student_id: int, course_id: Optional[int] = None
) -> AssignmentSummary:
    q = select(
        func.count(Assignment.id).label("total"),
        func.count(Assignment.id).filter(Assignment.is_submitted == True).label("submitted"),
        func.count(Assignment.id).filter(
            Assignment.is_submitted == True, Assignment.is_late == True
        ).label("late"),
        func.avg(
            Assignment.score / Assignment.max_score * 100
        ).filter(Assignment.score.isnot(None)).label("avg_score_pct"),
    ).where(Assignment.student_id == student_id)

    if course_id:
        q = q.where(Assignment.course_id == course_id)

    row = (await db.execute(q)).one()
    not_submitted = (row.total or 0) - (row.submitted or 0)
    on_time = (row.submitted or 0) - (row.late or 0)
    completion_rate = (row.submitted / row.total * 100) if row.total else 0.0
    on_time_rate = (on_time / row.submitted * 100) if row.submitted else 0.0

    return AssignmentSummary(
        student_id=student_id,
        course_id=course_id,
        total_assignments=row.total or 0,
        submitted=row.submitted or 0,
        not_submitted=not_submitted,
        late_submissions=row.late or 0,
        completion_rate=round(completion_rate, 2),
        on_time_rate=round(on_time_rate, 2),
        avg_score_pct=round(float(row.avg_score_pct), 2) if row.avg_score_pct else None,
    )
