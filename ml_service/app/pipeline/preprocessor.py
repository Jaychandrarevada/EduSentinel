"""
Sklearn preprocessing pipeline builder.

Separates numeric and binary features:
  - Numeric features  → StandardScaler
  - Binary flags      → passed through (already 0/1)
  - Class imbalance   → SMOTE oversampling (training only)

The ColumnTransformer preserves the original column order for SHAP.
"""
from __future__ import annotations

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, RobustScaler
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from app.pipeline.feature_engineering import FEATURE_COLS

# --------------------------------------------------------------------------- #
#  Column groups                                                               #
# --------------------------------------------------------------------------- #

# Continuous numeric features — will be scaled
NUMERIC_COLS = [
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
    "avg_ia_score",
    "ia_trend",
    "ia_consistency",
    "lms_engagement_score",
    "combined_risk_score",
]

# Binary flags — pass through without scaling
BINARY_COLS = [
    "attendance_risk_flag",
    "marks_risk_flag",
    "lms_inactivity_flag",
    "gpa_risk_flag",
]

assert set(NUMERIC_COLS + BINARY_COLS) == set(FEATURE_COLS), (
    "Column lists must cover exactly FEATURE_COLS"
)


# --------------------------------------------------------------------------- #
#  Preprocessor builders                                                       #
# --------------------------------------------------------------------------- #

def build_numeric_transformer() -> Pipeline:
    """Impute remaining nulls → robust scale (handles outliers)."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  RobustScaler()),   # Robust to outliers vs StandardScaler
    ])


def build_preprocessor() -> ColumnTransformer:
    """
    ColumnTransformer:
      numeric cols  → median impute + RobustScaler
      binary cols   → passthrough (no transformation)
    remainder       → drop (safety net)
    """
    return ColumnTransformer(
        transformers=[
            ("numeric", build_numeric_transformer(), NUMERIC_COLS),
            ("binary",  "passthrough",               BINARY_COLS),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def get_feature_names_out() -> list[str]:
    """Return feature names in the order the preprocessor outputs them."""
    return NUMERIC_COLS + BINARY_COLS


def build_base_pipeline(classifier) -> Pipeline:
    """
    Standard sklearn Pipeline (no SMOTE — for cross-validation and testing).
    Use this when evaluating on a held-out test set.
    """
    return Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier",   classifier),
    ])


def build_training_pipeline(
    classifier,
    smote_k: int = 5,
    random_state: int = 42,
) -> ImbPipeline:
    """
    Imbalanced-learn Pipeline with SMOTE.
    SMOTE is applied ONLY on training folds (not validation/test).
    Use this for model.fit() only.
    """
    return ImbPipeline([
        ("preprocessor", build_preprocessor()),
        ("smote",        SMOTE(
            k_neighbors=smote_k,
            random_state=random_state,
            sampling_strategy="auto",
        )),
        ("classifier",   classifier),
    ])
