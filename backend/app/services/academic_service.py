"""
Academic records service — marks ingestion and summary analytics.
"""
import io
from typing import Optional

import pandas as pd
import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.academic_record import AcademicRecord, ExamType
from app.schemas.academic import (
    AcademicRecordCreate,
    AcademicRecordOut,
    AcademicSummary,
    AcademicRecordBulkCreate,
)
from app.schemas.attendance import BulkUploadResult

log = structlog.get_logger()

_REQUIRED_CSV_COLS = {"roll_no", "course_code", "exam_type", "score", "max_score", "exam_date"}


async def add_record(
    db: AsyncSession, payload: AcademicRecordCreate, recorded_by: int
) -> AcademicRecordOut:
    record = AcademicRecord(**payload.model_dump(), recorded_by=recorded_by)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    await db.commit()
    return AcademicRecordOut.model_validate(record)


async def bulk_add_records(
    db: AsyncSession, payload: AcademicRecordBulkCreate, recorded_by: int
) -> BulkUploadResult:
    inserted = 0
    errors: list[str] = []

    for i, rec in enumerate(payload.records):
        try:
            record = AcademicRecord(**rec.model_dump(), recorded_by=recorded_by)
            db.add(record)
            inserted += 1
        except Exception as exc:
            errors.append(f"Row {i + 1}: {exc}")

    await db.commit()
    log.info("academic.bulk_insert", inserted=inserted, errors=len(errors))
    return BulkUploadResult(inserted=inserted, updated=0, skipped=0, errors=errors)


async def ingest_csv(
    db: AsyncSession,
    csv_bytes: bytes,
    student_lookup: dict,   # roll_no -> student_id
    course_lookup: dict,    # course_code -> course_id
    recorded_by: int,
) -> BulkUploadResult:
    """Parse and insert marks from a CSV file."""
    try:
        df = pd.read_csv(io.StringIO(csv_bytes.decode("utf-8")))
    except Exception as exc:
        raise ValidationError(f"Cannot parse CSV: {exc}")

    missing = _REQUIRED_CSV_COLS - set(df.columns)
    if missing:
        raise ValidationError(f"Missing columns: {missing}")

    inserted, skipped = 0, 0
    errors: list[str] = []

    for i, row in df.iterrows():
        roll_no = str(row["roll_no"]).strip()
        course_code = str(row["course_code"]).strip()

        student_id = student_lookup.get(roll_no)
        course_id = course_lookup.get(course_code)

        if not student_id:
            errors.append(f"Row {i + 2}: Unknown roll_no '{roll_no}'")
            skipped += 1
            continue
        if not course_id:
            errors.append(f"Row {i + 2}: Unknown course_code '{course_code}'")
            skipped += 1
            continue

        try:
            record = AcademicRecord(
                student_id=student_id,
                course_id=course_id,
                exam_type=ExamType(str(row["exam_type"]).strip().upper()),
                score=float(row["score"]),
                max_score=float(row["max_score"]),
                exam_date=pd.to_datetime(row["exam_date"]).date(),
                recorded_by=recorded_by,
            )
            db.add(record)
            inserted += 1
        except Exception as exc:
            errors.append(f"Row {i + 2}: {exc}")
            skipped += 1

    await db.commit()
    return BulkUploadResult(inserted=inserted, updated=0, skipped=skipped, errors=errors)


async def get_summary(
    db: AsyncSession, student_id: int, course_id: Optional[int] = None
) -> AcademicSummary:
    q = select(AcademicRecord).where(AcademicRecord.student_id == student_id)
    if course_id:
        q = q.where(AcademicRecord.course_id == course_id)

    records = (await db.execute(q)).scalars().all()
    if not records:
        return AcademicSummary(
            student_id=student_id, course_id=course_id,
            exam_counts={}, avg_percentage=0.0,
            highest_score_pct=0.0, lowest_score_pct=0.0, trend="no_data",
        )

    pcts = [r.percentage for r in records]
    by_type: dict = {}
    for r in records:
        by_type[r.exam_type] = by_type.get(r.exam_type, 0) + 1

    # Trend: compare first half avg vs second half avg
    mid = len(pcts) // 2
    first_half = sum(pcts[:mid]) / mid if mid else pcts[0]
    second_half = sum(pcts[mid:]) / (len(pcts) - mid) if mid else pcts[-1]
    diff = second_half - first_half
    trend = "improving" if diff > 3 else "declining" if diff < -3 else "stable"

    return AcademicSummary(
        student_id=student_id,
        course_id=course_id,
        exam_counts=by_type,
        avg_percentage=round(sum(pcts) / len(pcts), 2),
        highest_score_pct=round(max(pcts), 2),
        lowest_score_pct=round(min(pcts), 2),
        trend=trend,
    )
