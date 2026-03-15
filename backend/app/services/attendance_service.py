"""
Attendance service — ingestion (single + bulk CSV) and summary aggregation.
"""
import io
from typing import Optional

import pandas as pd
import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.attendance import Attendance, AttendanceStatus
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceBulkCreate,
    AttendanceOut,
    AttendanceSummary,
    BulkUploadResult,
)

log = structlog.get_logger()

_REQUIRED_CSV_COLS = {"roll_no", "course_code", "date", "status"}


async def add_single(
    db: AsyncSession, payload: AttendanceCreate, recorded_by: int
) -> AttendanceOut:
    """Upsert a single attendance record (insert or update on conflict)."""
    stmt = (
        pg_insert(Attendance)
        .values(
            student_id=payload.student_id,
            course_id=payload.course_id,
            date=payload.date,
            status=payload.status,
            recorded_by=recorded_by,
        )
        .on_conflict_do_update(
            constraint="uq_attendance_student_course_date",
            set_={"status": payload.status, "recorded_by": recorded_by},
        )
        .returning(Attendance)
    )
    result = await db.execute(stmt)
    await db.commit()
    record = result.scalar_one()
    return AttendanceOut.model_validate(record)


async def bulk_add(
    db: AsyncSession, payload: AttendanceBulkCreate, recorded_by: int
) -> BulkUploadResult:
    inserted, updated, errors = 0, 0, []

    for i, rec in enumerate(payload.records):
        try:
            stmt = (
                pg_insert(Attendance)
                .values(
                    student_id=rec.student_id,
                    course_id=rec.course_id,
                    date=rec.date,
                    status=rec.status,
                    recorded_by=recorded_by,
                )
                .on_conflict_do_update(
                    constraint="uq_attendance_student_course_date",
                    set_={"status": rec.status, "recorded_by": recorded_by},
                )
            )
            result = await db.execute(stmt)
            if result.rowcount == 1:
                inserted += 1
            else:
                updated += 1
        except Exception as exc:
            errors.append(f"Row {i + 1}: {exc}")

    await db.commit()
    log.info("attendance.bulk_upsert", inserted=inserted, updated=updated, errors=len(errors))
    return BulkUploadResult(inserted=inserted, updated=updated, skipped=0, errors=errors)


async def ingest_csv(
    db: AsyncSession,
    csv_bytes: bytes,
    student_lookup: dict,
    course_lookup: dict,
    recorded_by: int,
) -> BulkUploadResult:
    try:
        df = pd.read_csv(io.StringIO(csv_bytes.decode("utf-8")))
    except Exception as exc:
        raise ValidationError(f"Cannot parse CSV: {exc}")

    missing = _REQUIRED_CSV_COLS - set(df.columns)
    if missing:
        raise ValidationError(f"Missing columns: {missing}")

    records = []
    errors: list[str] = []

    for i, row in df.iterrows():
        roll_no = str(row["roll_no"]).strip()
        course_code = str(row["course_code"]).strip()
        status_raw = str(row["status"]).strip().upper()

        sid = student_lookup.get(roll_no)
        cid = course_lookup.get(course_code)

        if not sid:
            errors.append(f"Row {i + 2}: Unknown roll_no '{roll_no}'")
            continue
        if not cid:
            errors.append(f"Row {i + 2}: Unknown course_code '{course_code}'")
            continue
        if status_raw not in ("P", "A", "L"):
            errors.append(f"Row {i + 2}: Invalid status '{status_raw}'")
            continue

        records.append({
            "student_id": sid,
            "course_id": cid,
            "date": pd.to_datetime(row["date"]).date(),
            "status": status_raw,
            "recorded_by": recorded_by,
        })

    if records:
        stmt = (
            pg_insert(Attendance)
            .values(records)
            .on_conflict_do_update(
                constraint="uq_attendance_student_course_date",
                set_={"status": pg_insert(Attendance).excluded.status},
            )
        )
        await db.execute(stmt)
        await db.commit()

    return BulkUploadResult(
        inserted=len(records), updated=0, skipped=len(errors), errors=errors
    )


async def get_summary(
    db: AsyncSession,
    student_id: int,
    course_id: Optional[int] = None,
) -> AttendanceSummary:
    q = select(
        func.count(Attendance.id).label("total"),
        func.count(Attendance.id).filter(Attendance.status == AttendanceStatus.PRESENT).label("present"),
        func.count(Attendance.id).filter(Attendance.status == AttendanceStatus.ABSENT).label("absent"),
        func.count(Attendance.id).filter(Attendance.status == AttendanceStatus.LEAVE).label("leave"),
    ).where(Attendance.student_id == student_id)

    if course_id:
        q = q.where(Attendance.course_id == course_id)

    row = (await db.execute(q)).one()
    pct = round((row.present / row.total * 100), 2) if row.total else 0.0

    return AttendanceSummary(
        student_id=student_id,
        course_id=course_id,
        total_classes=row.total,
        present=row.present,
        absent=row.absent,
        leave=row.leave,
        attendance_pct=pct,
        is_at_risk=pct < 75.0,
    )
