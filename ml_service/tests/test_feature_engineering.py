"""Unit tests for feature engineering pipeline."""
import numpy as np
import pandas as pd
import pytest

from app.pipeline.feature_engineering import engineer_features, FEATURE_COLS
from app.pipeline.data_generator import generate_synthetic_data, RAW_FEATURE_COLS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def at_risk_row() -> pd.DataFrame:
    """A single student with at-risk profile."""
    return pd.DataFrame([{
        "student_id": 1,
        "attendance_pct": 52.0,
        "ia1_score": 28.0,
        "ia2_score": 31.0,
        "ia3_score": 25.0,
        "assignment_avg_score": 40.0,
        "assignment_completion_rate": 0.55,
        "lms_login_frequency": 0.3,
        "lms_time_spent_hours": 1.5,
        "lms_content_views": 4.0,
        "previous_gpa": 3.8,
        "label": 1,
    }])


@pytest.fixture
def safe_row() -> pd.DataFrame:
    """A single student with safe profile."""
    return pd.DataFrame([{
        "student_id": 2,
        "attendance_pct": 85.0,
        "ia1_score": 72.0,
        "ia2_score": 68.0,
        "ia3_score": 74.0,
        "assignment_avg_score": 78.0,
        "assignment_completion_rate": 0.92,
        "lms_login_frequency": 4.5,
        "lms_time_spent_hours": 12.0,
        "lms_content_views": 30.0,
        "previous_gpa": 7.5,
        "label": 0,
    }])


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    return generate_synthetic_data(n_samples=200, random_state=42)


# ---------------------------------------------------------------------------
# Column completeness
# ---------------------------------------------------------------------------

class TestFeatureColumns:
    def test_all_feature_cols_present(self, at_risk_row):
        result = engineer_features(at_risk_row)
        missing = [c for c in FEATURE_COLS if c not in result.columns]
        assert not missing, f"Missing columns: {missing}"

    def test_no_nulls_after_engineering(self, synthetic_df):
        result = engineer_features(synthetic_df)
        null_counts = result[FEATURE_COLS].isnull().sum()
        assert null_counts.sum() == 0, f"Null values found:\n{null_counts[null_counts > 0]}"

    def test_raw_cols_preserved(self, at_risk_row):
        result = engineer_features(at_risk_row)
        for col in RAW_FEATURE_COLS:
            assert col in result.columns


# ---------------------------------------------------------------------------
# Risk flag logic
# ---------------------------------------------------------------------------

class TestRiskFlags:
    def test_attendance_risk_flag_high_risk(self, at_risk_row):
        # attendance_pct=52 < 75 → flag=1
        result = engineer_features(at_risk_row)
        assert result.iloc[0]["attendance_risk_flag"] == 1

    def test_attendance_risk_flag_safe(self, safe_row):
        # attendance_pct=85 >= 75 → flag=0
        result = engineer_features(safe_row)
        assert result.iloc[0]["attendance_risk_flag"] == 0

    def test_marks_risk_flag_high_risk(self, at_risk_row):
        # avg_ia = (28+31+25)/3 ≈ 28 < 50 → flag=1
        result = engineer_features(at_risk_row)
        assert result.iloc[0]["marks_risk_flag"] == 1

    def test_marks_risk_flag_safe(self, safe_row):
        # avg_ia = (72+68+74)/3 ≈ 71.3 >= 50 → flag=0
        result = engineer_features(safe_row)
        assert result.iloc[0]["marks_risk_flag"] == 0

    def test_lms_inactivity_flag_high_risk(self, at_risk_row):
        # lms_login_frequency=0.3 < 1.0 → flag=1
        result = engineer_features(at_risk_row)
        assert result.iloc[0]["lms_inactivity_flag"] == 1

    def test_lms_inactivity_flag_safe(self, safe_row):
        # lms_login_frequency=4.5 >= 1.0 → flag=0
        result = engineer_features(safe_row)
        assert result.iloc[0]["lms_inactivity_flag"] == 0

    def test_gpa_risk_flag_at_risk(self, at_risk_row):
        # previous_gpa=3.8 < 4.0 → flag=1
        result = engineer_features(at_risk_row)
        assert result.iloc[0]["gpa_risk_flag"] == 1

    def test_gpa_risk_flag_safe(self, safe_row):
        # previous_gpa=7.5 >= 4.0 → flag=0
        result = engineer_features(safe_row)
        assert result.iloc[0]["gpa_risk_flag"] == 0


# ---------------------------------------------------------------------------
# Derived feature values
# ---------------------------------------------------------------------------

class TestDerivedFeatures:
    def test_avg_ia_score(self, at_risk_row):
        result = engineer_features(at_risk_row)
        expected = (28.0 + 31.0 + 25.0) / 3
        assert abs(result.iloc[0]["avg_ia_score"] - expected) < 1e-6

    def test_combined_risk_score_higher_for_at_risk(self, at_risk_row, safe_row):
        r_at_risk = engineer_features(at_risk_row).iloc[0]["combined_risk_score"]
        r_safe = engineer_features(safe_row).iloc[0]["combined_risk_score"]
        assert r_at_risk > r_safe, (
            f"Expected at-risk score ({r_at_risk:.3f}) > safe score ({r_safe:.3f})"
        )

    def test_combined_risk_score_bounds(self, synthetic_df):
        result = engineer_features(synthetic_df)
        scores = result["combined_risk_score"]
        assert (scores >= 0).all(), "combined_risk_score has negative values"
        assert (scores <= 1).all(), "combined_risk_score exceeds 1.0"

    def test_ia_consistency_non_negative(self, synthetic_df):
        result = engineer_features(synthetic_df)
        assert (result["ia_consistency"] >= 0).all()

    def test_lms_engagement_score_bounds(self, synthetic_df):
        result = engineer_features(synthetic_df)
        scores = result["lms_engagement_score"]
        assert (scores >= 0).all()
        assert (scores <= 1).all()


# ---------------------------------------------------------------------------
# NaN handling (rows with missing inputs)
# ---------------------------------------------------------------------------

class TestNaNHandling:
    def test_nan_in_lms_fields_produces_no_nulls(self, at_risk_row):
        row = at_risk_row.copy()
        row.loc[0, "lms_login_frequency"] = np.nan
        row.loc[0, "lms_time_spent_hours"] = np.nan
        result = engineer_features(row)
        assert result[FEATURE_COLS].isnull().sum().sum() == 0

    def test_nan_in_ia_scores_produces_no_nulls(self, at_risk_row):
        row = at_risk_row.copy()
        row.loc[0, "ia3_score"] = np.nan
        result = engineer_features(row)
        assert result[FEATURE_COLS].isnull().sum().sum() == 0
