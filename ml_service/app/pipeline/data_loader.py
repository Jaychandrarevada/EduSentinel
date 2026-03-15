"""
Data loader — pulls raw student records from PostgreSQL and returns a DataFrame.

Two modes:
  1. `load_from_db()`       — async, production path, reads live tables.
  2. `load_from_csv()`      — sync, reads a CSV export for offline training.
  3. `generate_synthetic()` — no DB required, for dev / CI.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import pandas as pd
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.data_generator import (
    GeneratorConfig,
    generate_student_data,
    RAW_FEATURE_COLS,
    TARGET_COL,
    STUDENT_ID_COL,
)

log = structlog.get_logger()

# --------------------------------------------------------------------------- #
#  SQL: aggregates features per student for the requested semester window      #
# --------------------------------------------------------------------------- #
_FEATURE_SQL = """
SELECT
    s.id                                                         AS student_id,
    s.department,
    s.semester,
    s.batch_year,

    -- Attendance
    COALESCE(
        COUNT(a.id) FILTER (WHERE a.status = 'P')::float
        / NULLIF(COUNT(a.id), 0) * 100,
        NULL
    )                                                            AS attendance_pct,

    -- Internal assessment scores (normalised 0-100)
    AVG(ar.score / NULLIF(ar.max_score, 0) * 100)
        FILTER (WHERE ar.exam_type = 'IA1')                      AS ia1_score,
    AVG(ar.score / NULLIF(ar.max_score, 0) * 100)
        FILTER (WHERE ar.exam_type = 'IA2')                      AS ia2_score,
    AVG(ar.score / NULLIF(ar.max_score, 0) * 100)
        FILTER (WHERE ar.exam_type = 'IA3')                      AS ia3_score,

    -- Assignment performance
    AVG(asn.score / NULLIF(asn.max_score, 0) * 100)
        FILTER (WHERE asn.score IS NOT NULL)                     AS assignment_avg_score,
    COUNT(asn.id) FILTER (WHERE asn.is_submitted = TRUE)::float
        / NULLIF(COUNT(asn.id), 0) * 100                        AS assignment_completion_rate,

    -- LMS activity (weekly averages)
    AVG(lms.login_count)                                         AS lms_login_frequency,
    AVG(lms.time_spent_minutes / 60.0)                          AS lms_time_spent_hours,
    AVG(lms.content_views)                                      AS lms_content_views,

    -- Previous GPA (mocked as avg marks from past semesters; replace with real GPA table)
    COALESCE(
        (SELECT AVG(ar2.score / NULLIF(ar2.max_score, 0) * 10)
         FROM academic_records ar2
         WHERE ar2.student_id = s.id
           AND ar2.exam_type = 'FINAL'),
        5.0
    )                                                            AS previous_gpa,

    -- Ground truth label
    CASE
        WHEN (
            COUNT(a.id) FILTER (WHERE a.status = 'P')::float
            / NULLIF(COUNT(a.id), 0)
        ) < 0.60
        OR AVG(ar.score / NULLIF(ar.max_score, 0)) < 0.40
        THEN 1 ELSE 0
    END                                                          AS is_at_risk

FROM students s
LEFT JOIN attendance_records a
       ON a.student_id = s.id
LEFT JOIN academic_records ar
       ON ar.student_id = s.id
LEFT JOIN assignments asn
       ON asn.student_id = s.id
LEFT JOIN lms_activity lms
       ON lms.student_id = s.id
          AND lms.date >= :since_date
WHERE (:semester IS NULL OR s.semester = :semester)
GROUP BY s.id
HAVING COUNT(a.id) >= :min_records
ORDER BY s.id
"""


async def load_from_db(
    db: AsyncSession,
    semester: Optional[int] = None,
    since_date: str = "2024-01-01",
    min_records: int = 10,
) -> pd.DataFrame:
    """Pull aggregated student features from live PostgreSQL tables."""
    result = await db.execute(
        text(_FEATURE_SQL),
        {"semester": semester, "since_date": since_date, "min_records": min_records},
    )
    rows = result.fetchall()
    df = pd.DataFrame(rows, columns=result.keys())
    log.info("data_loader.db_load", rows=len(df), semester=semester)
    return df


def load_from_csv(path: str | Path) -> pd.DataFrame:
    """Load pre-exported CSV (for offline experiments / Jupyter notebooks)."""
    df = pd.read_csv(path)
    log.info("data_loader.csv_load", path=str(path), rows=len(df))
    return df


def generate_synthetic(
    n_samples: int = 2000,
    at_risk_ratio: float = 0.25,
    random_state: int = 42,
) -> pd.DataFrame:
    """Return synthetic labelled DataFrame — no DB required."""
    cfg = GeneratorConfig(
        n_samples=n_samples,
        at_risk_ratio=at_risk_ratio,
        random_state=random_state,
    )
    df = generate_student_data(cfg)
    log.info(
        "data_loader.synthetic",
        rows=len(df),
        at_risk=int(df[TARGET_COL].sum()),
        ratio=round(df[TARGET_COL].mean(), 3),
    )
    return df
