"""
Data ingestion service — CSV parsing and bulk upserts for all data types.

Supports:
  - Attendance records (roll_no, course_code, date, status)
  - Academic / marks records (roll_no, course_code, exam_type, score, max_score, exam_date)
  - Assignment records (roll_no, course_code, title, score, max_score, is_submitted)
  - LMS activity records (roll_no, date, login_count, content_views, time_spent_minutes)
  - Unified student-data CSV (auto-create students + predict risk)
"""
from __future__ import annotations

import io
from datetime import datetime, date, timezone
from typing import Optional

import httpx
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ValidationError
from app.models.academic_record import AcademicRecord, ExamType
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.assignment import Assignment
from app.models.attendance import Attendance, AttendanceStatus
from app.models.lms_activity import LMSActivity
from app.models.prediction import Prediction, RiskLabel
from app.models.student import Student

log = structlog.get_logger()


# ── helpers ──────────────────────────────────────────────────────────────────

def _read_csv(csv_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(csv_bytes.decode("utf-8")))
    except Exception as exc:
        raise ValidationError(f"Cannot parse CSV: {exc}")


def _check_cols(df: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValidationError(f"Missing CSV columns: {', '.join(sorted(missing))}")


# ── attendance ────────────────────────────────────────────────────────────────

async def bulk_insert_attendance(
    db: AsyncSession,
    csv_bytes: bytes,
    student_lookup: dict[str, int],
    course_lookup: dict[str, int],
    recorded_by: int,
) -> dict:
    """Parse an attendance CSV and upsert all rows."""
    df = _read_csv(csv_bytes)
    _check_cols(df, {"roll_no", "course_code", "date", "status"})

    records, errors = [], []
    for i, row in df.iterrows():
        roll_no     = str(row["roll_no"]).strip()
        course_code = str(row["course_code"]).strip()
        status_raw  = str(row["status"]).strip().upper()

        sid = student_lookup.get(roll_no)
        cid = course_lookup.get(course_code)

        if not sid:
            errors.append(f"Row {i + 2}: Unknown roll_no '{roll_no}'")
            continue
        if not cid:
            errors.append(f"Row {i + 2}: Unknown course_code '{course_code}'")
            continue
        if status_raw not in ("P", "A", "L"):
            errors.append(f"Row {i + 2}: Invalid status '{status_raw}' (expected P/A/L)")
            continue

        try:
            rec_date = pd.to_datetime(row["date"]).date()
        except Exception:
            errors.append(f"Row {i + 2}: Invalid date '{row['date']}'")
            continue

        records.append({
            "student_id": sid,
            "course_id": cid,
            "date": rec_date,
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

    log.info("ingest.attendance", inserted=len(records), errors=len(errors))
    return {"inserted": len(records), "skipped": len(errors), "errors": errors}


# ── academic / marks ──────────────────────────────────────────────────────────

async def bulk_insert_academic(
    db: AsyncSession,
    csv_bytes: bytes,
    student_lookup: dict[str, int],
    course_lookup: dict[str, int],
    recorded_by: int,
) -> dict:
    """Parse a marks CSV and insert AcademicRecord rows."""
    df = _read_csv(csv_bytes)
    _check_cols(df, {"roll_no", "course_code", "exam_type", "score", "max_score", "exam_date"})

    valid_exam_types = {e.value for e in ExamType}
    records, errors = [], []

    for i, row in df.iterrows():
        roll_no     = str(row["roll_no"]).strip()
        course_code = str(row["course_code"]).strip()
        exam_type   = str(row["exam_type"]).strip().upper()

        sid = student_lookup.get(roll_no)
        cid = course_lookup.get(course_code)

        if not sid:
            errors.append(f"Row {i + 2}: Unknown roll_no '{roll_no}'")
            continue
        if not cid:
            errors.append(f"Row {i + 2}: Unknown course_code '{course_code}'")
            continue
        if exam_type not in valid_exam_types:
            errors.append(f"Row {i + 2}: Invalid exam_type '{exam_type}' (expected {valid_exam_types})")
            continue

        try:
            score     = float(row["score"])
            max_score = float(row["max_score"])
            exam_date = pd.to_datetime(row["exam_date"]).date()
        except Exception as exc:
            errors.append(f"Row {i + 2}: Data error — {exc}")
            continue

        if max_score <= 0 or score < 0 or score > max_score:
            errors.append(f"Row {i + 2}: score={score} out of range [0, {max_score}]")
            continue

        records.append(AcademicRecord(
            student_id=sid,
            course_id=cid,
            exam_type=ExamType(exam_type),
            score=score,
            max_score=max_score,
            exam_date=exam_date,
            remarks=str(row.get("remarks", "")).strip() or None,
            recorded_by=recorded_by,
        ))

    if records:
        db.add_all(records)
        await db.commit()

    log.info("ingest.academic", inserted=len(records), errors=len(errors))
    return {"inserted": len(records), "skipped": len(errors), "errors": errors}


# ── assignments ───────────────────────────────────────────────────────────────

async def bulk_insert_assignments(
    db: AsyncSession,
    csv_bytes: bytes,
    student_lookup: dict[str, int],
    course_lookup: dict[str, int],
    recorded_by: int,
) -> dict:
    """Parse an assignments CSV and insert Assignment rows."""
    df = _read_csv(csv_bytes)
    _check_cols(df, {"roll_no", "course_code", "title", "score", "max_score", "is_submitted"})

    records, errors = [], []

    for i, row in df.iterrows():
        roll_no     = str(row["roll_no"]).strip()
        course_code = str(row["course_code"]).strip()

        sid = student_lookup.get(roll_no)
        cid = course_lookup.get(course_code)

        if not sid:
            errors.append(f"Row {i + 2}: Unknown roll_no '{roll_no}'")
            continue
        if not cid:
            errors.append(f"Row {i + 2}: Unknown course_code '{course_code}'")
            continue

        try:
            score        = float(row["score"]) if pd.notna(row.get("score")) else None
            max_score    = float(row["max_score"])
            is_submitted = str(row["is_submitted"]).strip().lower() in ("1", "true", "yes", "y")
        except Exception as exc:
            errors.append(f"Row {i + 2}: Data error — {exc}")
            continue

        submitted_at = None
        if pd.notna(row.get("submitted_at", None)):
            try:
                submitted_at = pd.to_datetime(row["submitted_at"]).to_pydatetime()
            except Exception:
                pass

        records.append(Assignment(
            student_id=sid,
            course_id=cid,
            title=str(row["title"]).strip(),
            score=score,
            max_score=max_score,
            is_submitted=is_submitted,
            is_late=str(row.get("is_late", "false")).strip().lower() in ("1", "true", "yes", "y"),
            submitted_at=submitted_at,
            recorded_by=recorded_by,
        ))

    if records:
        db.add_all(records)
        await db.commit()

    log.info("ingest.assignments", inserted=len(records), errors=len(errors))
    return {"inserted": len(records), "skipped": len(errors), "errors": errors}


# ── LMS activity ──────────────────────────────────────────────────────────────

async def bulk_insert_lms(
    db: AsyncSession,
    csv_bytes: bytes,
    student_lookup: dict[str, int],
    recorded_by: int,
) -> dict:
    """Parse an LMS activity CSV and upsert LMSActivity rows."""
    df = _read_csv(csv_bytes)
    _check_cols(df, {"roll_no", "date", "login_count", "time_spent_minutes"})

    records, errors = [], []

    for i, row in df.iterrows():
        roll_no = str(row["roll_no"]).strip()
        sid = student_lookup.get(roll_no)

        if not sid:
            errors.append(f"Row {i + 2}: Unknown roll_no '{roll_no}'")
            continue

        try:
            rec_date           = pd.to_datetime(row["date"]).date()
            login_count        = int(row.get("login_count", 0))
            content_views      = int(row.get("content_views", 0))
            quiz_attempts      = int(row.get("quiz_attempts", 0))
            forum_posts        = int(row.get("forum_posts", 0))
            time_spent_minutes = float(row.get("time_spent_minutes", 0.0))
        except Exception as exc:
            errors.append(f"Row {i + 2}: Data error — {exc}")
            continue

        records.append({
            "student_id":         sid,
            "date":               rec_date,
            "login_count":        login_count,
            "content_views":      content_views,
            "quiz_attempts":      quiz_attempts,
            "forum_posts":        forum_posts,
            "time_spent_minutes": time_spent_minutes,
        })

    if records:
        stmt = (
            pg_insert(LMSActivity)
            .values(records)
            .on_conflict_do_update(
                constraint="uq_lms_student_date",
                set_={
                    "login_count":        pg_insert(LMSActivity).excluded.login_count,
                    "content_views":      pg_insert(LMSActivity).excluded.content_views,
                    "quiz_attempts":      pg_insert(LMSActivity).excluded.quiz_attempts,
                    "forum_posts":        pg_insert(LMSActivity).excluded.forum_posts,
                    "time_spent_minutes": pg_insert(LMSActivity).excluded.time_spent_minutes,
                },
            )
        )
        await db.execute(stmt)
        await db.commit()

    log.info("ingest.lms", inserted=len(records), errors=len(errors))
    return {"inserted": len(records), "skipped": len(errors), "errors": errors}


# ── unified student-data CSV ──────────────────────────────────────────────────

_UNIFIED_REQUIRED = {
    "student_name", "roll_no", "attendance",
    "internal_score", "assignment_score", "lms_activity",
    "engagement_time", "previous_gpa",
}

_RISK_THRESHOLDS = [
    (0.70, "HIGH"),
    (0.40, "MEDIUM"),
    (0.00, "LOW"),
]


def _rule_based_risk(
    attendance: float,
    internal_score: float,
    assignment_score: float,
    lms_activity: float,
    previous_gpa: float,
) -> tuple[float, str]:
    """
    Heuristic fallback risk scoring when ML service is unavailable.

    Returns (risk_score, risk_label) where risk_score is in [0, 1].
    """
    score = 0.0
    score += max(0.0, (75.0 - attendance)  / 75.0) * 0.30  # attendance weight 30%
    score += max(0.0, (60.0 - internal_score) / 60.0) * 0.25
    score += max(0.0, (60.0 - assignment_score) / 60.0) * 0.20
    score += max(0.0, (50.0 - lms_activity)  / 50.0) * 0.15
    score += max(0.0, (6.0  - previous_gpa)  / 6.0)  * 0.10

    risk_score = min(round(score, 4), 1.0)
    for threshold, label in _RISK_THRESHOLDS:
        if risk_score >= threshold:
            return risk_score, label
    return risk_score, "LOW"


async def ingest_student_data_csv(
    db: AsyncSession,
    csv_bytes: bytes,
    recorded_by: int,
    semester: str,
    department: str = "General",
    batch_year: Optional[int] = None,
) -> dict:
    """
    Parse a unified student-data CSV and:
      1. Auto-create students that do not exist yet.
      2. Store aggregated academic/LMS data as Prediction inputs.
      3. Call ML service (or fallback to heuristic) to compute risk.
      4. Persist Prediction records; create Alerts for HIGH-risk students.

    CSV format:
        student_name, roll_no, email (optional), attendance (%),
        internal_score (0-100), assignment_score (0-100),
        lms_activity (0-100), engagement_time (hours), previous_gpa (0-10)
    """
    df = _read_csv(csv_bytes)
    _check_cols(df, _UNIFIED_REQUIRED)

    if batch_year is None:
        batch_year = datetime.now().year

    # Pre-load existing students by roll_no
    existing_rows = (await db.execute(select(Student.roll_no, Student.id))).all()
    student_lookup: dict[str, int] = {r.roll_no: r.id for r in existing_rows}

    predictions_created = 0
    students_created    = 0
    errors: list[str]   = []

    for i, row in df.iterrows():
        try:
            roll_no     = str(row["roll_no"]).strip()
            full_name   = str(row["student_name"]).strip()
            email_raw   = str(row.get("email", "")).strip()
            attendance  = float(row["attendance"])
            int_score   = float(row["internal_score"])
            asgn_score  = float(row["assignment_score"])
            lms_act     = float(row["lms_activity"])
            eng_time    = float(row["engagement_time"])
            prev_gpa    = float(row["previous_gpa"])
        except Exception as exc:
            errors.append(f"Row {i + 2}: Parse error — {exc}")
            continue

        # Create student if not exists
        if roll_no not in student_lookup:
            email = email_raw if email_raw and "@" in email_raw else f"{roll_no.lower()}@edusentinel.local"
            new_student = Student(
                roll_no=roll_no,
                full_name=full_name,
                email=email,
                department=department,
                semester=int(semester.split("-")[0]) if semester[0].isdigit() else 1,
                batch_year=batch_year,
            )
            db.add(new_student)
            await db.flush()  # get the new id without full commit
            student_lookup[roll_no] = new_student.id
            students_created += 1

        sid = student_lookup[roll_no]

        # Build ML payload
        logins_per_week = round(lms_act / 100 * 7, 2)
        content_views   = round(lms_act / 100 * 50, 2)

        ml_payload = {
            "student_id":              sid,
            "attendance_pct":          attendance,
            "ia1_score":               int_score,
            "ia2_score":               int_score,
            "ia3_score":               int_score,
            "assignment_avg_score":    asgn_score,
            "assignment_completion_rate": round(asgn_score / 100, 4),
            "lms_login_frequency":     logins_per_week,
            "lms_time_spent_hours":    eng_time,
            "lms_content_views":       content_views,
            "previous_gpa":            prev_gpa,
        }

        # Try ML service; fall back to heuristic
        risk_score: float
        risk_label: str
        contributing_factors: list

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{settings.ML_SERVICE_URL}/predict/single",
                    json=ml_payload,
                )
                resp.raise_for_status()
                ml_data = resp.json()

            risk_score = ml_data["risk_score"]
            risk_label = ml_data["risk_label"]
            contributing_factors = ml_data.get("contributing_factors", [])
            model_version = ml_data.get("model_version", "ml-service")

        except Exception:
            risk_score, risk_label = _rule_based_risk(
                attendance, int_score, asgn_score, lms_act, prev_gpa
            )
            contributing_factors = [
                {"feature": "attendance_pct",       "impact": 0.30, "value": attendance},
                {"feature": "internal_score",        "impact": 0.25, "value": int_score},
                {"feature": "assignment_avg_score",  "impact": 0.20, "value": asgn_score},
                {"feature": "lms_engagement_score",  "impact": 0.15, "value": lms_act},
                {"feature": "previous_gpa",          "impact": 0.10, "value": prev_gpa},
            ]
            model_version = "heuristic-v1"

        prediction = Prediction(
            student_id=sid,
            semester=semester,
            risk_score=risk_score,
            risk_label=RiskLabel(risk_label),
            contributing_factors=contributing_factors,
            model_version=model_version,
            predicted_at=datetime.now(timezone.utc),
        )
        db.add(prediction)

        if risk_label == "HIGH":
            top_factor = contributing_factors[0]["feature"] if contributing_factors else "N/A"
            alert = Alert(
                student_id=sid,
                alert_type=AlertType.HIGH_RISK_PREDICTED,
                severity=AlertSeverity.HIGH,
                message=(
                    f"{full_name} predicted HIGH risk (score: {risk_score:.2%}) "
                    f"in {semester}. Top factor: {top_factor}"
                ),
            )
            db.add(alert)

        predictions_created += 1

    await db.commit()

    log.info(
        "ingest.student_data",
        students_created=students_created,
        predictions=predictions_created,
        errors=len(errors),
    )
    return {
        "students_created": students_created,
        "predictions_created": predictions_created,
        "skipped": len(errors),
        "errors": errors,
    }
