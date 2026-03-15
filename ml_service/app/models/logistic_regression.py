"""
Logistic Regression model definition.

Role in the pipeline: baseline / sanity check.
Advantages: fast, interpretable coefficients, well-calibrated probabilities.
Tuning: regularisation strength C, solver, max_iter.
"""
from __future__ import annotations

from sklearn.linear_model import LogisticRegression

# Hyperparameter grid for GridSearchCV / RandomizedSearchCV
LR_PARAM_GRID = {
    "classifier__C":         [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
    "classifier__penalty":   ["l2"],
    "classifier__solver":    ["lbfgs"],
    "classifier__max_iter":  [500, 1000],
}

LR_RANDOM_GRID = {
    "classifier__C":         [0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0],
    "classifier__max_iter":  [300, 500, 1000],
}


def build_logistic_regression(
    C: float = 1.0,
    max_iter: int = 1000,
    random_state: int = 42,
    class_weight: str = "balanced",
) -> LogisticRegression:
    """
    L2 Logistic Regression.

    class_weight='balanced' automatically compensates for label imbalance
    by weighting minority class inversely proportional to its frequency.
    """
    return LogisticRegression(
        C=C,
        penalty="l2",
        solver="lbfgs",
        max_iter=max_iter,
        class_weight=class_weight,
        random_state=random_state,
        n_jobs=-1,
    )
