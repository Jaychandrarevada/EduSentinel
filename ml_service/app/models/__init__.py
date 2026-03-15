"""ML model registry — export all model factory functions."""
from app.models.logistic_regression import build_logistic_regression
from app.models.random_forest import build_random_forest
from app.models.gradient_boosting import build_gradient_boosting
from app.models.xgboost_model import build_xgboost

__all__ = [
    "build_logistic_regression",
    "build_random_forest",
    "build_gradient_boosting",
    "build_xgboost",
]

# Catalogue: name → factory function + hyperparameter grid
MODEL_CATALOGUE = {
    "logistic_regression": {
        "factory": build_logistic_regression,
        "description": "L2-regularised Logistic Regression (baseline, interpretable)",
    },
    "random_forest": {
        "factory": build_random_forest,
        "description": "Random Forest — ensemble of decision trees, handles non-linearity",
    },
    "gradient_boosting": {
        "factory": build_gradient_boosting,
        "description": "sklearn GradientBoostingClassifier — sequential boosting",
    },
    "xgboost": {
        "factory": build_xgboost,
        "description": "XGBoost — fast gradient boosting with L1/L2 regularisation",
    },
}
