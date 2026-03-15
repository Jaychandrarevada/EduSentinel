"""
Random Forest model definition.

Role: Strong ensemble baseline, naturally handles non-linear interactions.
Feature importance is built-in and interpretable.
Tuning: n_estimators, max_depth, min_samples_split, max_features.
"""
from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier

RF_RANDOM_GRID = {
    "classifier__n_estimators":      [100, 200, 300, 500],
    "classifier__max_depth":         [None, 5, 10, 15, 20],
    "classifier__min_samples_split": [2, 5, 10],
    "classifier__min_samples_leaf":  [1, 2, 4],
    "classifier__max_features":      ["sqrt", "log2", 0.5],
}


def build_random_forest(
    n_estimators: int = 300,
    max_depth: int | None = None,
    min_samples_split: int = 5,
    min_samples_leaf: int = 2,
    max_features: str = "sqrt",
    class_weight: str = "balanced",
    random_state: int = 42,
) -> RandomForestClassifier:
    """
    Random Forest with balanced class weights.

    n_jobs=-1 uses all CPU cores.
    oob_score=True enables free out-of-bag generalisation estimate.
    """
    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        class_weight=class_weight,
        oob_score=True,
        random_state=random_state,
        n_jobs=-1,
    )
