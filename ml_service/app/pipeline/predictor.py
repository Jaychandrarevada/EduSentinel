"""
Predictor -- loads a trained pipeline and runs inference with SHAP explanations.

Every prediction returns:
  - risk_score:           float 0.0-1.0 (P(at_risk))
  - risk_label:           "LOW" | "MEDIUM" | "HIGH"
  - contributing_factors: top-3 feature contributions (SHAP values)

SHAP TreeExplainer is used for tree-based models (RF, GB, XGBoost).
KernelExplainer is used as fallback for Logistic Regression.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import structlog

from app.pipeline.feature_engineering import (
    engineer_features,
    FEATURE_COLS,
    STUDENT_ID_COL,
)
from app.pipeline.preprocessor import get_feature_names_out

log = structlog.get_logger()

_RISK_THRESHOLDS = {"HIGH": 0.65, "MEDIUM": 0.35}

_FEATURE_LABELS: dict[str, str] = {
    "attendance_pct":             "Attendance Percentage",
    "ia1_score":                  "IA1 Score",
    "ia2_score":                  "IA2 Score",
    "ia3_score":                  "IA3 Score",
    "assignment_avg_score":       "Average Assignment Score",
    "assignment_completion_rate": "Assignment Completion Rate",
    "lms_login_frequency":        "LMS Login Frequency (per week)",
    "lms_time_spent_hours":       "LMS Time Spent (hours/week)",
    "lms_content_views":          "LMS Content Views (per week)",
    "previous_gpa":               "Previous Semester GPA",
    "avg_ia_score":               "Average IA Score",
    "ia_trend":                   "IA Score Trend (slope)",
    "ia_consistency":             "IA Score Consistency",
    "attendance_risk_flag":       "Attendance Below Threshold",
    "marks_risk_flag":            "Marks Below Threshold",
    "lms_engagement_score":       "LMS Engagement Score",
    "lms_inactivity_flag":        "LMS Inactivity Flag",
    "gpa_risk_flag":              "GPA Below Threshold",
    "combined_risk_score":        "Combined Risk Score",
}

_TREE_CLF_NAMES = {
    "RandomForestClassifier",
    "HistGradientBoostingClassifier",
    "XGBClassifier",
    "GradientBoostingClassifier",
    "ExtraTreesClassifier",
}


def _score_to_label(score: float, threshold: Optional[float] = None) -> str:
    if threshold is not None:
        return "HIGH" if score >= threshold else ("MEDIUM" if score >= 0.35 else "LOW")
    return ("HIGH" if score >= _RISK_THRESHOLDS["HIGH"]
            else "MEDIUM" if score >= _RISK_THRESHOLDS["MEDIUM"]
            else "LOW")


def _extract_clf(pipeline) -> object:
    return list(pipeline.named_steps.values())[-1]


def _extract_preprocessor(pipeline) -> object:
    return list(pipeline.named_steps.values())[0]


def _build_shap_explainer(clf, X_bg: np.ndarray):
    """Instantiate the appropriate SHAP explainer for the classifier type."""
    import shap
    clf_name = type(clf).__name__
    if clf_name in _TREE_CLF_NAMES:
        return shap.TreeExplainer(clf)
    # Fallback: model-agnostic KernelExplainer (slower)
    return shap.KernelExplainer(clf.predict_proba, X_bg[:100])


def _shap_top_factors(
    shap_row: np.ndarray,
    feat_values: np.ndarray,
    feat_names: list[str],
    top_n: int = 3,
) -> list[dict]:
    indices = np.argsort(np.abs(shap_row))[::-1][:top_n]
    return [
        {
            "feature":   feat_names[i],
            "label":     _FEATURE_LABELS.get(feat_names[i], feat_names[i]),
            "impact":    round(float(shap_row[i]), 4),
            "value":     round(float(feat_values[i]), 4),
            "direction": "increases_risk" if shap_row[i] > 0 else "decreases_risk",
        }
        for i in indices
    ]


def predict_single(
    pipeline,
    raw_features: dict,
    threshold: float = 0.5,
    explain: bool = True,
) -> dict:
    """
    Predict at-risk status for a single student.

    raw_features: dict containing RAW_INPUT_COLS keys from feature_engineering.
    Returns: {risk_score, risk_label, contributing_factors}
    """
    df = pd.DataFrame([raw_features])
    df = engineer_features(df)
    X  = df[FEATURE_COLS]

    y_proba = float(pipeline.predict_proba(X)[0, 1])
    label   = _score_to_label(y_proba, threshold)

    factors: list[dict] = []
    if explain:
        try:
            prep          = _extract_preprocessor(pipeline)
            clf           = _extract_clf(pipeline)
            X_transformed = prep.transform(X)
            explainer     = _build_shap_explainer(clf, X_transformed)
            shap_vals     = explainer.shap_values(X_transformed)
            shap_row      = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]
            factors       = _shap_top_factors(shap_row, X_transformed[0], get_feature_names_out())
        except Exception as exc:
            log.warning("shap.single_failed", error=str(exc))

    return {
        "risk_score":           round(y_proba, 4),
        "risk_label":           label,
        "contributing_factors": factors,
    }


def predict_batch(
    pipeline,
    feature_df: pd.DataFrame,
    threshold: float = 0.5,
    explain: bool = True,
) -> list[dict]:
    """
    Batch inference on a DataFrame of raw student features.

    feature_df must contain RAW_INPUT_COLS and optionally STUDENT_ID_COL.
    Returns predictions sorted by risk_score descending.
    """
    if feature_df.empty:
        return []

    df        = engineer_features(feature_df.copy())
    X         = df[FEATURE_COLS]
    y_probas  = pipeline.predict_proba(X)[:, 1]
    feat_names = get_feature_names_out()

    # Batch SHAP
    shap_matrix: Optional[np.ndarray] = None
    X_transformed: Optional[np.ndarray] = None

    if explain:
        try:
            prep          = _extract_preprocessor(pipeline)
            clf           = _extract_clf(pipeline)
            X_transformed = prep.transform(X)
            explainer     = _build_shap_explainer(clf, X_transformed)
            sv            = explainer.shap_values(X_transformed)
            shap_matrix   = sv[1] if isinstance(sv, list) else sv
        except Exception as exc:
            log.warning("shap.batch_failed", error=str(exc))

    results = []
    for i, (idx, row) in enumerate(df.iterrows()):
        score = float(y_probas[i])
        label = _score_to_label(score, threshold)

        factors: list[dict] = []
        if shap_matrix is not None and X_transformed is not None:
            factors = _shap_top_factors(shap_matrix[i], X_transformed[i], feat_names)

        sid = row.get(STUDENT_ID_COL, i) if STUDENT_ID_COL in df.columns else i
        results.append({
            "student_id":           int(sid) if not pd.isna(sid) else i,
            "risk_score":           round(score, 4),
            "risk_label":           label,
            "contributing_factors": factors,
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    log.info("predictor.batch_complete",
             n=len(results),
             high=sum(1 for r in results if r["risk_label"] == "HIGH"),
             medium=sum(1 for r in results if r["risk_label"] == "MEDIUM"))
    return results
