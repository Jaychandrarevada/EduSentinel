"""
Synthetic student data generator for development, testing, and initial model training.

Generates realistic at-risk distributions with configurable class imbalance.
Mirrors the exact feature schema produced by the real data loader so the
pipeline is identical in dev and production.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

# --------------------------------------------------------------------------- #
#  Schema constants — must stay in sync with feature_engineering.FEATURE_COLS #
# --------------------------------------------------------------------------- #
RAW_FEATURE_COLS = [
    "attendance_pct",
    "ia1_score",
    "ia2_score",
    "ia3_score",
    "assignment_avg_score",
    "assignment_completion_rate",
    "lms_login_frequency",       # logins / week
    "lms_time_spent_hours",      # hours / week on platform
    "lms_content_views",         # pages/videos viewed / week
    "previous_gpa",              # 0.0–10.0 scale
]

TARGET_COL = "is_at_risk"
STUDENT_ID_COL = "student_id"


@dataclass
class GeneratorConfig:
    n_samples: int = 2000
    at_risk_ratio: float = 0.25        # 25 % at-risk (realistic imbalance)
    noise_level: float = 0.05          # Gaussian noise factor
    random_state: int = 42
    include_student_id: bool = True


def _clip(arr: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.clip(arr, lo, hi)


def generate_student_data(cfg: GeneratorConfig = GeneratorConfig()) -> pd.DataFrame:
    """
    Generate a synthetic labelled dataset.

    At-risk students are characterised by:
        - Low attendance  (< 65 %)
        - Lower IA scores (mean ~ 35/100)
        - Poor assignment completion / LMS engagement
        - Lower previous GPA
    Non-at-risk students show the complementary pattern with natural overlap.
    """
    rng = np.random.default_rng(cfg.random_state)
    n_at_risk = int(cfg.n_samples * cfg.at_risk_ratio)
    n_safe = cfg.n_samples - n_at_risk

    def _gauss(mean, std, n, lo=0.0, hi=100.0):
        return _clip(rng.normal(mean, std, n), lo, hi)

    # ── At-risk students ──────────────────────────────────────────────────
    ar = pd.DataFrame({
        "attendance_pct":            _gauss(52,  15, n_at_risk, 0, 100),
        "ia1_score":                 _gauss(34,  12, n_at_risk, 0, 100),
        "ia2_score":                 _gauss(31,  13, n_at_risk, 0, 100),
        "ia3_score":                 _gauss(29,  14, n_at_risk, 0, 100),
        "assignment_avg_score":      _gauss(38,  18, n_at_risk, 0, 100),
        "assignment_completion_rate":_gauss(48,  22, n_at_risk, 0, 100),
        "lms_login_frequency":       _gauss(1.2, 0.9, n_at_risk, 0, 20),
        "lms_time_spent_hours":      _gauss(1.0, 0.8, n_at_risk, 0, 40),
        "lms_content_views":         _gauss(3,   3,   n_at_risk, 0, 50),
        "previous_gpa":              _gauss(4.5, 1.8, n_at_risk, 0, 10),
        TARGET_COL: 1,
    })

    # ── Non-at-risk students ──────────────────────────────────────────────
    safe = pd.DataFrame({
        "attendance_pct":            _gauss(82,  10, n_safe, 0, 100),
        "ia1_score":                 _gauss(68,  14, n_safe, 0, 100),
        "ia2_score":                 _gauss(66,  14, n_safe, 0, 100),
        "ia3_score":                 _gauss(65,  15, n_safe, 0, 100),
        "assignment_avg_score":      _gauss(72,  15, n_safe, 0, 100),
        "assignment_completion_rate":_gauss(84,  14, n_safe, 0, 100),
        "lms_login_frequency":       _gauss(5.5, 2.0, n_safe, 0, 20),
        "lms_time_spent_hours":      _gauss(5.0, 2.5, n_safe, 0, 40),
        "lms_content_views":         _gauss(14,  6,   n_safe, 0, 50),
        "previous_gpa":              _gauss(7.2, 1.4, n_safe, 0, 10),
        TARGET_COL: 0,
    })

    df = pd.concat([ar, safe], ignore_index=True)

    # Shuffle
    df = df.sample(frac=1, random_state=cfg.random_state).reset_index(drop=True)

    # Add student IDs
    if cfg.include_student_id:
        df.insert(0, STUDENT_ID_COL, range(1000, 1000 + len(df)))

    # Inject realistic missing values (~ 8 % of LMS fields, ~ 3 % of scores)
    for col in ["lms_login_frequency", "lms_time_spent_hours", "lms_content_views"]:
        mask = rng.random(len(df)) < 0.08
        df.loc[mask, col] = np.nan

    for col in ["ia3_score", "assignment_avg_score"]:
        mask = rng.random(len(df)) < 0.03
        df.loc[mask, col] = np.nan

    return df


def get_train_test_split(
    cfg: GeneratorConfig = GeneratorConfig(),
    test_size: float = 0.2,
    val_size: float = 0.1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return train / validation / test DataFrames from synthetic data."""
    from sklearn.model_selection import train_test_split

    df = generate_student_data(cfg)
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size + val_size, stratify=y,
        random_state=cfg.random_state,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_test, y_test, test_size=test_size / (test_size + val_size),
        stratify=y_test, random_state=cfg.random_state,
    )

    train = pd.concat([X_train, y_train], axis=1)
    val   = pd.concat([X_val,   y_val],   axis=1)
    test  = pd.concat([X_test,  y_test],  axis=1)
    return train, val, test
