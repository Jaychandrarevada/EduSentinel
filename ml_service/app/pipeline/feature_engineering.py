"""
Feature engineering — transforms raw student metrics into model-ready features.

Design principles:
  - Every transform is a pure function (no side effects)
  - Missing values handled explicitly before downstream pipeline
  - Domain knowledge encoded as interpretable features
  - All thresholds are documented and justified
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
#  Feature column groups                                                       #
# --------------------------------------------------------------------------- #

# Raw columns from DB / CSV (must be present before engineering)
RAW_INPUT_COLS = [
    "attendance_pct",
    "ia1_score",
    "ia2_score",
    "ia3_score",
    "assignment_avg_score",
    "assignment_completion_rate",
    "lms_login_frequency",
    "lms_time_spent_hours",
    "lms_content_views",
    "previous_gpa",
]

# Engineered features added by this module
ENGINEERED_COLS = [
    "avg_ia_score",           # Mean of IA1/IA2/IA3
    "ia_trend",               # Slope of IA1→IA2→IA3 (positive = improving)
    "ia_consistency",         # Std dev of IA scores (lower = more consistent)
    "attendance_risk_flag",   # 1 if attendance < 75 %
    "marks_risk_flag",        # 1 if avg_ia_score < 50
    "lms_engagement_score",   # Composite 0–100
    "lms_inactivity_flag",    # 1 if login < 1 / week
    "gpa_risk_flag",          # 1 if previous_gpa < 4.0
    "combined_risk_score",    # Weighted sum of all risk flags
]

# Final feature set fed into the sklearn pipeline
FEATURE_COLS: list[str] = RAW_INPUT_COLS + ENGINEERED_COLS

TARGET_COL = "is_at_risk"
STUDENT_ID_COL = "student_id"

# Imputation fill values (conservative / worst-case for unknown values)
IMPUTATION_VALUES: dict[str, float] = {
    "attendance_pct":             0.0,
    "ia1_score":                  0.0,
    "ia2_score":                  0.0,
    "ia3_score":                  0.0,
    "assignment_avg_score":       0.0,
    "assignment_completion_rate": 0.0,
    "lms_login_frequency":        0.0,
    "lms_time_spent_hours":       0.0,
    "lms_content_views":          0.0,
    "previous_gpa":               5.0,   # median GPA assumption
}

# Risk thresholds (domain-knowledge driven)
_ATTENDANCE_RISK_THRESHOLD      = 75.0   # regulatory minimum in many universities
_MARKS_RISK_THRESHOLD           = 50.0   # below 50 % → struggling
_LMS_INACTIVITY_THRESHOLD       = 1.0    # < 1 login/week → disengaged
_GPA_RISK_THRESHOLD             = 4.0    # below 4.0/10 → academically weak


# --------------------------------------------------------------------------- #
#  Core transform functions                                                    #
# --------------------------------------------------------------------------- #

def impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill NaN with conservative defaults.
    Unknown scores become 0 (worst case); unknown GPA becomes median.
    """
    df = df.copy()
    for col, fill_val in IMPUTATION_VALUES.items():
        if col in df.columns:
            df[col] = df[col].fillna(fill_val)
    return df


def engineer_ia_features(df: pd.DataFrame) -> pd.DataFrame:
    """Internal Assessment composite features."""
    df = df.copy()

    ia_cols = [c for c in ["ia1_score", "ia2_score", "ia3_score"] if c in df.columns]

    # Average IA score
    df["avg_ia_score"] = df[ia_cols].mean(axis=1)

    # Trend: positive slope = improving, negative = declining
    # Uses least-squares over [ia1, ia2, ia3]
    if len(ia_cols) >= 2:
        n = len(ia_cols)
        x = np.arange(n, dtype=float)
        x_mean = x.mean()
        x_var = ((x - x_mean) ** 2).sum()

        def _slope(row: pd.Series) -> float:
            vals = row[ia_cols].values.astype(float)
            return float(np.dot(vals - vals.mean(), x - x_mean) / x_var)

        df["ia_trend"] = df.apply(_slope, axis=1)
    else:
        df["ia_trend"] = 0.0

    # Consistency — lower std = more consistent performance
    if len(ia_cols) >= 2:
        df["ia_consistency"] = df[ia_cols].std(axis=1).fillna(0.0)
    else:
        df["ia_consistency"] = 0.0

    return df


def engineer_risk_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Binary risk flags encoding domain knowledge thresholds."""
    df = df.copy()
    df["attendance_risk_flag"] = (df["attendance_pct"] < _ATTENDANCE_RISK_THRESHOLD).astype(int)
    df["marks_risk_flag"]      = (df["avg_ia_score"]   < _MARKS_RISK_THRESHOLD).astype(int)
    df["lms_inactivity_flag"]  = (df["lms_login_frequency"] < _LMS_INACTIVITY_THRESHOLD).astype(int)
    df["gpa_risk_flag"]        = (df["previous_gpa"]   < _GPA_RISK_THRESHOLD).astype(int)
    return df


def engineer_lms_engagement(df: pd.DataFrame) -> pd.DataFrame:
    """
    Composite LMS engagement score (0–100).

    Components:
      40 % — login frequency  (normalised, cap at 10 logins/week)
      35 % — content views    (normalised, cap at 20 views/week)
      25 % — time spent       (normalised, cap at 10 hours/week)
    """
    df = df.copy()
    login_score  = df["lms_login_frequency"].clip(0, 10) / 10 * 40
    view_score   = df["lms_content_views"].clip(0, 20)   / 20 * 35
    time_score   = df["lms_time_spent_hours"].clip(0, 10) / 10 * 25
    df["lms_engagement_score"] = login_score + view_score + time_score
    return df


def engineer_combined_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted combined risk score (0–1).

    Weights reflect feature importance from domain knowledge:
      Attendance  → 30 %
      IA marks    → 30 %
      LMS         → 20 %
      Assignments → 10 %
      GPA         → 10 %
    """
    df = df.copy()
    att_norm  = 1 - (df["attendance_pct"].clip(0, 100) / 100)
    mark_norm = 1 - (df["avg_ia_score"].clip(0, 100) / 100)
    lms_norm  = 1 - (df["lms_engagement_score"].clip(0, 100) / 100)
    asgn_norm = 1 - (df["assignment_completion_rate"].clip(0, 100) / 100)
    gpa_norm  = 1 - (df["previous_gpa"].clip(0, 10) / 10)

    df["combined_risk_score"] = (
        0.30 * att_norm
        + 0.30 * mark_norm
        + 0.20 * lms_norm
        + 0.10 * asgn_norm
        + 0.10 * gpa_norm
    )
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master feature engineering function.
    Applies all transforms in the correct order.
    Returns a DataFrame with FEATURE_COLS + TARGET_COL (if present).
    """
    df = impute_missing_values(df)
    df = engineer_ia_features(df)
    df = engineer_risk_flags(df)
    df = engineer_lms_engagement(df)
    df = engineer_combined_risk(df)

    # Verify all expected columns are present
    missing = set(FEATURE_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Feature engineering produced missing columns: {missing}")

    return df


def split_X_y(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split engineered DataFrame into features X and target y."""
    X = df[FEATURE_COLS].copy()
    y = df[TARGET_COL].copy() if TARGET_COL in df.columns else None
    return X, y
