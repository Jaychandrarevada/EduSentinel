"""
Student data generator — generates realistic academic data and inserts into DB.

Usage:
    result = await generate_and_insert_students(db, num_students=500, semester="2025-ODD")
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from uuid import uuid4

import numpy as np
import structlog
from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_record import AcademicRecord
from app.models.assignment import Assignment
from app.models.attendance import Attendance, AttendanceStatus
from app.models.lms_activity import LMSActivity
from app.models.prediction import Prediction, RiskLabel
from app.models.student import Student

log = structlog.get_logger()
fake = Faker(locale="en_IN")


def _clamp(v: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, v)))


def _risk_label(attendance: float, internal: float, assignment: float) -> str:
    if attendance < 60 or (internal < 50 and assignment < 50):
        return RiskLabel.HIGH
    if attendance < 75 or internal < 60:
        return RiskLabel.MEDIUM
    return RiskLabel.LOW


def _risk_score(attendance: float, internal: float, assignment: float, lms: float) -> float:
    """Heuristic risk probability [0, 1]."""
    score = 0.0
    score += max(0, (75 - attendance) / 75) * 0.35
    score += max(0, (60 - internal) / 60) * 0.30
    score += max(0, (70 - assignment) / 70) * 0.20
    score += max(0, (50 - lms) / 50) * 0.15
    return _clamp(score, 0.01, 0.99)


async def generate_and_insert_students(
    db: AsyncSession,
    num_students: int,
    semester: str = "2025-ODD",
) -> dict:
    """Generate `num_students` synthetic students and persist all related records."""
    rng = np.random.default_rng(seed=random.randint(0, 999999))
    batch_year = 2022
    today = date.today()

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    created = 0

    # Build distributions
    attendances   = rng.normal(75, 15, num_students).clip(20, 100)
    internals     = rng.normal(65, 18, num_students).clip(0, 100)
    assignments   = rng.normal(70, 16, num_students).clip(0, 100)
    lms_scores    = rng.normal(60, 22, num_students).clip(0, 100)
    prev_gpas     = rng.normal(6.5, 1.5, num_students).clip(0, 10)

    for i in range(num_students):
        roll_no = f"GEN{batch_year}{(i + 1):04d}-{uuid4().hex[:4].upper()}"
        email   = f"student.gen{i + 1}.{uuid4().hex[:6]}@test.edu"

        att  = float(attendances[i])
        ia   = float(internals[i])
        asgn = float(assignments[i])
        lms  = float(lms_scores[i])
        gpa  = float(prev_gpas[i])

        label = _risk_label(att, ia, asgn)
        score = _risk_score(att, ia, asgn, lms)

        # ── Student ──────────────────────────────────────────────────────
        student = Student(
            roll_no=roll_no,
            full_name=fake.name(),
            email=email,
            phone=fake.phone_number()[:20],
            department=random.choice(["Computer Science", "Electronics", "Mechanical", "Civil", "IT"]),
            semester=random.randint(1, 8),
            batch_year=batch_year,
        )
        db.add(student)
        try:
            await db.flush()  # get student.id without committing
        except Exception:
            await db.rollback()
            continue  # skip duplicates

        sid = student.id

        # ── Attendance records (last 30 days, ~3 per week) ───────────────
        present_prob = att / 100
        for day_offset in range(0, 30, 2):
            rec_date = today - timedelta(days=day_offset)
            if rec_date.weekday() >= 5:
                continue
            status_val = random.choices(
                [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.LEAVE],
                weights=[present_prob, (1 - present_prob) * 0.8, (1 - present_prob) * 0.2],
            )[0]
            db.add(Attendance(
                student_id=sid,
                course_id=1,  # default course; seeder creates course id=1
                date=rec_date,
                status=status_val,
            ))

        # ── Academic records ─────────────────────────────────────────────
        for exam_type, score_val in [("IA1", ia), ("IA2", ia + rng.normal(0, 5))]:
            db.add(AcademicRecord(
                student_id=sid,
                course_id=1,
                exam_type=exam_type,
                score=round(_clamp(score_val, 0, 100) * 0.6, 1),  # out of 60
                max_score=60.0,
                exam_date=today - timedelta(days=random.randint(0, 60)),
            ))

        # ── Assignments ───────────────────────────────────────────────────
        for j in range(3):
            submitted = random.random() < (asgn / 100)
            db.add(Assignment(
                student_id=sid,
                course_id=1,
                title=f"Assignment {j + 1}",
                due_date=today - timedelta(days=random.randint(5, 45)),
                is_submitted=submitted,
                score=round(_clamp(asgn + rng.normal(0, 8), 0, 100) * 0.1, 1) if submitted else None,
                max_score=10.0,
            ))

        # ── LMS activity ──────────────────────────────────────────────────
        db.add(LMSActivity(
            student_id=sid,
            date=today - timedelta(days=random.randint(0, 7)),
            login_count=max(0, int(rng.normal(lms / 20, 1))),
            content_views=max(0, int(rng.normal(lms / 10, 2))),
            quiz_attempts=max(0, int(rng.normal(lms / 30, 0.5))),
            forum_posts=max(0, int(rng.normal(lms / 50, 0.3))),
            time_spent_minutes=max(0, int(rng.normal(lms * 1.5, 20))),
        ))

        # ── Prediction ────────────────────────────────────────────────────
        factors = [
            {"feature": "attendance_pct",           "impact": round(abs(75 - att) / 75 * 0.35, 3), "value": round(att, 1)},
            {"feature": "ia1_score",                 "impact": round(abs(60 - ia) / 60 * 0.30, 3),  "value": round(ia, 1)},
            {"feature": "assignment_avg_score",      "impact": round(abs(70 - asgn) / 70 * 0.20, 3),"value": round(asgn, 1)},
            {"feature": "lms_engagement_score",      "impact": round(abs(50 - lms) / 50 * 0.15, 3), "value": round(lms, 1)},
            {"feature": "previous_gpa",              "impact": round((gpa / 10) * 0.08, 3),          "value": round(gpa, 2)},
        ]
        db.add(Prediction(
            student_id=sid,
            semester=semester,
            risk_score=round(score, 3),
            risk_label=label,
            contributing_factors=factors,
            model_version="generator-v1",
        ))

        counts[label] += 1
        created += 1

    await db.commit()
    log.info("data_generator.complete", created=created, semester=semester, **counts)

    return {
        "students_created": created,
        "semester": semester,
        "high_risk":   counts["HIGH"],
        "medium_risk": counts["MEDIUM"],
        "low_risk":    counts["LOW"],
    }
