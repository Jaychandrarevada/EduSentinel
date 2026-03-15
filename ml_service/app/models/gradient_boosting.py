"""
Gradient Boosting model definition (sklearn's HistGradientBoostingClassifier).

Uses histogram-based splitting — fast on large datasets, native NaN support.
Tuning: learning_rate, max_iter, max_depth, l2_regularization.
"""
from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingClassifier

GB_RANDOM_GRID = {
    "classifier__learning_rate":     [0.01, 0.05, 0.1, 0.2],
    "classifier__max_iter":          [100, 200, 300, 500],
    "classifier__max_depth":         [3, 5, 7, None],
    "classifier__min_samples_leaf":  [10, 20, 30, 50],
    "classifier__l2_regularization": [0.0, 0.1, 1.0, 10.0],
}


def build_gradient_boosting(
    learning_rate: float = 0.05,
    max_iter: int = 300,
    max_depth: int | None = 5,
    min_samples_leaf: int = 20,
    l2_regularization: float = 0.1,
    class_weight: str = "balanced",
    random_state: int = 42,
) -> HistGradientBoostingClassifier:
    """
    Histogram-based Gradient Boosting.

    Advantages over classic GBM:
      - Faster training (bin-based splits)
      - Native NaN handling (no explicit imputation needed)
      - Built-in early stopping via validation_fraction
    class_weight='balanced' supported natively since sklearn 1.2.
    """
    return HistGradientBoostingClassifier(
        learning_rate=learning_rate,
        max_iter=max_iter,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        l2_regularization=l2_regularization,
        class_weight=class_weight,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=random_state,
    )
