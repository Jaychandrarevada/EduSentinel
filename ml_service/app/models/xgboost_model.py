"""
XGBoost model definition.

Best-in-class gradient boosting with L1/L2 regularisation.
Handles class imbalance via scale_pos_weight.
Tuning: n_estimators, learning_rate, max_depth, subsample, colsample_bytree.
"""
from __future__ import annotations

import numpy as np

XGBOOST_RANDOM_GRID = {
    "classifier__n_estimators":    [100, 200, 300, 500],
    "classifier__learning_rate":   [0.01, 0.05, 0.1, 0.2],
    "classifier__max_depth":       [3, 4, 5, 6, 7],
    "classifier__subsample":       [0.6, 0.7, 0.8, 0.9, 1.0],
    "classifier__colsample_bytree":[0.6, 0.7, 0.8, 0.9, 1.0],
    "classifier__reg_alpha":       [0, 0.01, 0.1, 1.0],
    "classifier__reg_lambda":      [0.1, 1.0, 5.0, 10.0],
    "classifier__min_child_weight":[1, 3, 5, 7],
}


def build_xgboost(
    n_estimators: int = 300,
    learning_rate: float = 0.05,
    max_depth: int = 5,
    subsample: float = 0.8,
    colsample_bytree: float = 0.8,
    reg_alpha: float = 0.1,
    reg_lambda: float = 1.0,
    scale_pos_weight: float | None = None,   # auto-computed if None
    random_state: int = 42,
):
    """
    XGBoost Classifier.

    scale_pos_weight = n_negative / n_positive handles imbalance without SMOTE.
    If None, ratio is set to 3.0 (approximating 25 % at-risk class).

    Falls back gracefully if xgboost is not installed.
    """
    try:
        from xgboost import XGBClassifier
    except ImportError:
        raise ImportError(
            "xgboost is not installed. Run: pip install xgboost"
        )

    spw = scale_pos_weight if scale_pos_weight is not None else 3.0

    return XGBClassifier(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_alpha=reg_alpha,
        reg_lambda=reg_lambda,
        scale_pos_weight=spw,
        eval_metric="logloss",
        use_label_encoder=False,
        tree_method="hist",          # GPU-ready: change to "gpu_hist"
        random_state=random_state,
        n_jobs=-1,
    )
