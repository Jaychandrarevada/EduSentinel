"""LMS activity service — ingestion and engagement analytics."""
from datetime import date, timedelta
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lms_activity import LMSActivity
from app.schemas.lms_activity import (
    LMSActivityCreate,
    LMSActivityBulkCreate,
    LMSActivityOut,
    LMSActivitySummary,
)
from app.schemas.attendance import BulkUploadResult

log = structlog.get_logger()


async def upsert_activity(
    db: AsyncSession, payload: LMSActivityCreate
) -> LMSActivityOut:
    """Upsert daily LMS activity (one record per student per day)."""
    stmt = (
        pg_insert(LMSActivity)
        .values(**payload.model_dump())
        .on_conflict_do_update(
            constraint="uq_lms_student_date",
            set_={
                "login_count": pg_insert(LMSActivity).excluded.login_count,
                "content_views": pg_insert(LMSActivity).excluded.content_views,
                "quiz_attempts": pg_insert(LMSActivity).excluded.quiz_attempts,
                "forum_posts": pg_insert(LMSActivity).excluded.forum_posts,
                "time_spent_minutes": pg_insert(LMSActivity).excluded.time_spent_minutes,
                "last_login": pg_insert(LMSActivity).excluded.last_login,
            },
        )
        .returning(LMSActivity)
    )
    result = await db.execute(stmt)
    await db.commit()
    return LMSActivityOut.model_validate(result.scalar_one())


async def bulk_upsert(
    db: AsyncSession, payload: LMSActivityBulkCreate
) -> BulkUploadResult:
    inserted, errors = 0, []
    for i, rec in enumerate(payload.records):
        try:
            stmt = (
                pg_insert(LMSActivity)
                .values(**rec.model_dump())
                .on_conflict_do_update(
                    constraint="uq_lms_student_date",
                    set_={
                        "login_count": rec.login_count,
                        "content_views": rec.content_views,
                        "time_spent_minutes": rec.time_spent_minutes,
                    },
                )
            )
            await db.execute(stmt)
            inserted += 1
        except Exception as exc:
            errors.append(f"Row {i + 1}: {exc}")
    await db.commit()
    return BulkUploadResult(inserted=inserted, updated=0, skipped=len(errors), errors=errors)


async def get_summary(
    db: AsyncSession, student_id: int, days: int = 90
) -> LMSActivitySummary:
    since = date.today() - timedelta(days=days)
    q = select(
        func.count(LMSActivity.id).label("days_active"),
        func.avg(LMSActivity.login_count).label("avg_logins"),
        func.avg(LMSActivity.content_views).label("avg_views"),
        func.sum(LMSActivity.time_spent_minutes).label("total_mins"),
        func.max(LMSActivity.date).label("last_active_date"),
    ).where(
        LMSActivity.student_id == student_id,
        LMSActivity.date >= since,
        LMSActivity.login_count > 0,
    )
    row = (await db.execute(q)).one()

    days_since = None
    if row.last_active_date:
        days_since = (date.today() - row.last_active_date).days

    avg_logins = float(row.avg_logins or 0)
    avg_views = float(row.avg_views or 0)
    total_hours = float(row.total_mins or 0) / 60

    # Composite engagement score 0–100
    login_score = min(1.0, avg_logins / 5) * 40
    view_score = min(1.0, avg_views / 10) * 40
    recency_score = max(0.0, (1 - (days_since or 0) / 30)) * 20 if days_since is not None else 0

    return LMSActivitySummary(
        student_id=student_id,
        days_active=row.days_active or 0,
        avg_logins_per_week=round(avg_logins * 7, 2),
        avg_content_views=round(avg_views, 2),
        total_time_hours=round(total_hours, 2),
        days_since_last_login=days_since,
        engagement_score=round(login_score + view_score + recency_score, 2),
    )
