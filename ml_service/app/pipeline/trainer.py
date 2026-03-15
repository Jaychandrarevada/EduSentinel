"""
Training orchestrator -- trains all 4 models, compares, selects best,
tunes decision threshold, and saves to the model registry.

Run:
  python -m app.pipeline.trainer               # synthetic data (default)
  python -m app.pipeline.trainer --source csv --path data.csv
  python -m app.pipeline.trainer --tune        # with hyperparameter search
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import structlog
from sklearn.model_selection import train_test_split, RandomizedSearchCV

from app.models import (
    build_logistic_regression,
    build_random_forest,
    build_gradient_boosting,
    build_xgboost,
)
from app.pipeline.data_loader import generate_synthetic, load_from_csv
from app.pipeline.feature_engineering import engineer_features, TARGET_COL, FEATURE_COLS
from app.pipeline.preprocessor import build_training_pipeline, build_base_pipeline
from app.pipeline.evaluator import (
    ModelMetrics,
    cross_validate_model,
    evaluate_on_test,
    find_optimal_threshold,
    log_metrics,
    print_evaluation_report,
    print_classification_report,
    plot_roc_curves,
    plot_feature_importance,
)
from app.registry.model_registry import ModelRegistry

log = structlog.get_logger()

MIN_SAMPLES    = 50
PRIMARY_METRIC = "roc_auc"

_MODEL_FACTORIES = {
    "logistic_regression": build_logistic_regression,
    "random_forest":       build_random_forest,
    "gradient_boosting":   build_gradient_boosting,
    "xgboost":             build_xgboost,
}

_SEARCH_GRIDS = {
    "logistic_regression": {
        "classifier__C":        [0.001, 0.01, 0.1, 1.0, 10.0],
        "classifier__max_iter": [500, 1000],
    },
    "random_forest": {
        "classifier__n_estimators":      [100, 200, 300],
        "classifier__max_depth":         [None, 5, 10, 20],
        "classifier__min_samples_split": [2, 5, 10],
        "classifier__min_samples_leaf":  [1, 2, 4],
    },
    "gradient_boosting": {
        "classifier__learning_rate": [0.01, 0.05, 0.1],
        "classifier__max_iter":      [100, 200, 300],
        "classifier__max_depth":     [3, 5, 7],
    },
    "xgboost": {
        "classifier__n_estimators":  [100, 200, 300],
        "classifier__learning_rate": [0.01, 0.05, 0.1],
        "classifier__max_depth":     [3, 5, 6],
        "classifier__subsample":     [0.7, 0.8, 0.9],
    },
}


def _split_dataset(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size:  float = 0.10,
    random_state: int = 42,
):
    """Three-way stratified split: train / val / test."""
    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    X_tv, X_test, y_tv, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    rel_val = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_tv, y_tv, test_size=rel_val, stratify=y_tv, random_state=random_state
    )
    log.info(
        "data_split",
        train=len(X_train), val=len(X_val), test=len(X_test),
        at_risk_train=int(y_train.sum()), at_risk_test=int(y_test.sum()),
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def _train_single_model(
    name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    tune_hyperparams: bool = False,
    n_iter: int = 20,
    random_state: int = 42,
) -> tuple[object, ModelMetrics]:
    """Train one model: optional HP tuning, CV, threshold optimisation, test eval."""
    log.info("trainer.model_start", model=name)
    factory        = _MODEL_FACTORIES[name]
    train_pipeline = build_training_pipeline(factory(random_state=random_state), random_state=random_state)
    eval_pipeline  = build_base_pipeline(factory(random_state=random_state))
    cv_results: dict = {}

    if tune_hyperparams and name in _SEARCH_GRIDS:
        log.info("trainer.hyperparameter_search", model=name, n_iter=n_iter)
        search = RandomizedSearchCV(
            eval_pipeline,
            param_distributions=_SEARCH_GRIDS[name],
            n_iter=n_iter,
            scoring="roc_auc",
            cv=3,
            refit=True,
            n_jobs=-1,
            random_state=random_state,
        )
        search.fit(X_train, y_train)
        log.info("trainer.best_params", model=name, params=search.best_params_)
        fitted_model = search.best_estimator_
    else:
        cv_results = cross_validate_model(eval_pipeline, X_train, y_train, n_splits=5)
        log.info("trainer.cv_complete", model=name, **cv_results)
        train_pipeline.fit(X_train, y_train)
        fitted_model = train_pipeline

    optimal_thr = find_optimal_threshold(fitted_model, X_val, y_val, target_recall=0.85)
    metrics     = evaluate_on_test(fitted_model, X_test, y_test, name, threshold=optimal_thr)
    metrics.optimal_threshold = optimal_thr

    for k, v in cv_results.items():
        if hasattr(metrics, k):
            setattr(metrics, k, v)

    log_metrics(metrics)
    print_classification_report(fitted_model, X_test, y_test, name, threshold=optimal_thr)
    return fitted_model, metrics


def select_best_model(
    trained: dict[str, tuple[object, ModelMetrics]],
) -> tuple[str, object, ModelMetrics]:
    """
    Select best model:
    1. Prefer models that pass all quality gates
    2. Sort by ROC-AUC, break ties by recall
    """
    passing   = {k: v for k, v in trained.items() if v[1].passes_gates}
    candidate = passing if passing else trained
    best_name = max(
        candidate,
        key=lambda k: (candidate[k][1].roc_auc, candidate[k][1].recall),
    )
    return best_name, candidate[best_name][0], candidate[best_name][1]


def extract_feature_importances(model, feature_names: list[str]):
    """Pull importances from the fitted classifier step, if available."""
    import numpy as np
    try:
        clf = model.named_steps.get("classifier") or model[-1]
        if hasattr(clf, "feature_importances_"):
            return clf.feature_importances_
        if hasattr(clf, "coef_"):
            return np.abs(clf.coef_[0])
    except Exception:
        pass
    return None


def run_training_pipeline(
    source: str = "synthetic",
    csv_path: Optional[str] = None,
    n_samples: int = 2000,
    tune_hyperparams: bool = False,
    save_plots: bool = True,
    artifact_dir: str = "./artifacts",
    random_state: int = 42,
) -> dict:
    """
    Full end-to-end training pipeline:
      1. Load data
      2. Feature engineering
      3. Train / Val / Test split (stratified)
      4. Train all 4 models (LR, RF, GB, XGBoost) with 5-fold CV
      5. Tune decision threshold on validation set
      6. Select best model by ROC-AUC (quality-gate aware)
      7. Persist to model registry
      8. Save ROC + feature importance plots
    """
    log.info("training_pipeline.start", source=source)

    raw_df = generate_synthetic(n_samples=n_samples) if source == "synthetic" else load_from_csv(csv_path)

    if len(raw_df) < MIN_SAMPLES:
        raise ValueError(f"Insufficient data: {len(raw_df)} (min {MIN_SAMPLES})")

    df = engineer_features(raw_df)
    log.info("training_pipeline.data_ready",
             total=len(df), at_risk=int(df[TARGET_COL].sum()),
             pct=round(df[TARGET_COL].mean() * 100, 1))

    X_train, X_val, X_test, y_train, y_val, y_test = _split_dataset(df, random_state=random_state)

    trained: dict[str, tuple[object, ModelMetrics]] = {}
    for model_name in _MODEL_FACTORIES:
        try:
            model, metrics = _train_single_model(
                name=model_name,
                X_train=X_train, y_train=y_train,
                X_val=X_val,     y_val=y_val,
                X_test=X_test,   y_test=y_test,
                tune_hyperparams=tune_hyperparams,
                random_state=random_state,
            )
            trained[model_name] = (model, metrics)
        except Exception as exc:
            log.error("trainer.model_failed", model=model_name, error=str(exc))

    if not trained:
        raise RuntimeError("All models failed to train")

    best_name, best_model, best_metrics = select_best_model(trained)
    all_metrics = [v[1] for v in trained.values()]
    print_evaluation_report(all_metrics, best_name)

    registry = ModelRegistry(artifact_dir=artifact_dir)
    version  = f"v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    registry.save(
        pipeline=best_model,
        version=version,
        model_name=best_name,
        metrics=best_metrics.to_dict(),
        feature_cols=FEATURE_COLS,
        threshold=best_metrics.optimal_threshold,
    )

    if save_plots:
        Path(artifact_dir).mkdir(parents=True, exist_ok=True)
        plot_roc_curves(
            [(m, X_test, y_test, n) for n, (m, _) in trained.items()],
            save_path=f"{artifact_dir}/roc_curves_{version}.png",
        )
        imps = extract_feature_importances(best_model, FEATURE_COLS)
        if imps is not None:
            plot_feature_importance(
                FEATURE_COLS, imps, best_name,
                save_path=f"{artifact_dir}/feature_importance_{version}.png",
            )

    log.info("training_pipeline.complete",
             version=version, best=best_name, roc_auc=best_metrics.roc_auc,
             recall=best_metrics.recall, threshold=best_metrics.optimal_threshold)

    return {
        "version":      version,
        "best_model":   best_name,
        "metrics":      best_metrics.to_dict(),
        "all_metrics":  [m.to_dict() for m in all_metrics],
        "passes_gates": best_metrics.passes_gates,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train student at-risk models")
    parser.add_argument("--source",    default="synthetic", choices=["synthetic", "csv"])
    parser.add_argument("--path",      default=None,        help="CSV file path")
    parser.add_argument("--n",         type=int, default=2000)
    parser.add_argument("--tune",      action="store_true")
    parser.add_argument("--artifacts", default="./artifacts")
    args = parser.parse_args()

    result = run_training_pipeline(
        source=args.source,
        csv_path=args.path,
        n_samples=args.n,
        tune_hyperparams=args.tune,
        artifact_dir=args.artifacts,
    )
    print(f"\nVersion    : {result['version']}")
    print(f"Best model : {result['best_model']}")
    print(f"ROC-AUC    : {result['metrics']['roc_auc']}")
    print(f"Recall     : {result['metrics']['recall']}")
    print(f"Threshold  : {result['metrics']['optimal_threshold']}")
    print(f"Gates OK   : {result['passes_gates']}")
