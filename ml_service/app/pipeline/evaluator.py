"""
Model evaluation -- computes, logs, and validates all classification metrics.

Evaluation philosophy for at-risk prediction:
  - RECALL is the primary metric (we must not miss at-risk students)
  - PRECISION matters to prevent alert fatigue
  - AUC-ROC captures overall discrimination ability
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
import structlog

log = structlog.get_logger()

# Quality gate thresholds
QUALITY_GATES = {
    "recall":    0.80,
    "precision": 0.65,
    "f1":        0.72,
    "roc_auc":   0.85,
    "accuracy":  0.78,
}


@dataclass
class ModelMetrics:
    model_name: str
    accuracy:         float = 0.0
    precision:        float = 0.0
    recall:           float = 0.0
    f1:               float = 0.0
    roc_auc:          float = 0.0
    avg_precision:    float = 0.0
    cv_recall_mean:     float = 0.0
    cv_recall_std:      float = 0.0
    cv_roc_auc_mean:    float = 0.0
    cv_roc_auc_std:     float = 0.0
    cv_f1_mean:         float = 0.0
    cv_precision_mean:  float = 0.0
    cv_accuracy_mean:   float = 0.0
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    optimal_threshold: float = 0.5
    passes_gates: bool = False
    failed_gates: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def summary_line(self) -> str:
        gate = "PASS" if self.passes_gates else "FAIL"
        return (
            f"[{gate}] {self.model_name:28s} "
            f"AUC={self.roc_auc:.4f}  "
            f"Recall={self.recall:.4f}  "
            f"Prec={self.precision:.4f}  "
            f"F1={self.f1:.4f}  "
            f"Acc={self.accuracy:.4f}"
        )


def evaluate_on_test(model, X_test, y_test, model_name, threshold=0.5):
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred  = (y_proba >= threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    metrics = ModelMetrics(
        model_name      = model_name,
        accuracy        = round(accuracy_score(y_test, y_pred), 4),
        precision       = round(precision_score(y_test, y_pred, zero_division=0), 4),
        recall          = round(recall_score(y_test, y_pred, zero_division=0), 4),
        f1              = round(f1_score(y_test, y_pred, zero_division=0), 4),
        roc_auc         = round(roc_auc_score(y_test, y_proba), 4),
        avg_precision   = round(average_precision_score(y_test, y_proba), 4),
        optimal_threshold = threshold,
        tp=int(tp), fp=int(fp), tn=int(tn), fn=int(fn),
    )
    failed = [g for g, thr in QUALITY_GATES.items() if getattr(metrics, g, 0) < thr]
    metrics.failed_gates  = failed
    metrics.passes_gates  = len(failed) == 0
    return metrics


def cross_validate_model(pipeline, X, y, n_splits=5, random_state=42):
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    results = cross_validate(
        pipeline, X, y,
        cv=cv,
        scoring=["roc_auc", "recall", "precision", "f1", "accuracy"],
        return_train_score=True,
        n_jobs=-1,
    )
    return {
        "cv_roc_auc_mean":   round(float(np.mean(results["test_roc_auc"])),   4),
        "cv_roc_auc_std":    round(float(np.std(results["test_roc_auc"])),    4),
        "cv_recall_mean":    round(float(np.mean(results["test_recall"])),    4),
        "cv_recall_std":     round(float(np.std(results["test_recall"])),     4),
        "cv_f1_mean":        round(float(np.mean(results["test_f1"])),        4),
        "cv_precision_mean": round(float(np.mean(results["test_precision"])), 4),
        "cv_accuracy_mean":  round(float(np.mean(results["test_accuracy"])),  4),
        "cv_roc_auc_train_mean": round(float(np.mean(results["train_roc_auc"])), 4),
    }


def find_optimal_threshold(model, X_val, y_val, target_recall=0.85):
    y_proba = model.predict_proba(X_val)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_proba)
    valid_idx = np.where(recalls[:-1] >= target_recall)[0]
    if len(valid_idx) == 0:
        log.warning("threshold_opt.no_valid_threshold", target_recall=target_recall)
        return 0.5
    best_idx = valid_idx[np.argmax(precisions[valid_idx])]
    optimal  = float(thresholds[best_idx])
    log.info("threshold_opt.found", threshold=round(optimal, 3),
             recall=round(float(recalls[best_idx]), 3),
             precision=round(float(precisions[best_idx]), 3))
    return optimal


def log_metrics(metrics: ModelMetrics) -> None:
    log.info(
        "evaluation.metrics",
        model=metrics.model_name,
        accuracy=metrics.accuracy,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        roc_auc=metrics.roc_auc,
        passes_gates=metrics.passes_gates,
        failed_gates=metrics.failed_gates,
        confusion_matrix={"tp": metrics.tp, "fp": metrics.fp,
                          "tn": metrics.tn, "fn": metrics.fn},
    )


def print_evaluation_report(all_metrics, best_model_name):
    print("
" + "=" * 80)
    print("  MODEL EVALUATION SUMMARY")
    print("=" * 80)
    for m in sorted(all_metrics, key=lambda x: x.roc_auc, reverse=True):
        marker = " <-- BEST" if m.model_name == best_model_name else ""
        print(m.summary_line() + marker)
    print("=" * 80)
    print(f"
Quality Gates: {QUALITY_GATES}")


def print_classification_report(model, X_test, y_test, model_name, threshold=0.5):
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred  = (y_proba >= threshold).astype(int)
    print(f"
{'='*60}")
    print(f" Classification Report: {model_name}")
    print(f" Decision threshold: {threshold}")
    print(f"{'='*60}")
    print(classification_report(y_test, y_pred, target_names=["Not At-Risk", "At-Risk"]))


def plot_roc_curves(results, save_path=None):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Random (AUC=0.50)")
    for model, X_test, y_test, name in results:
        y_proba = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        auc = roc_auc_score(y_test, y_proba)
        ax.plot(fpr, tpr, lw=2, label=f"{name} (AUC={auc:.3f})")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves -- At-Risk Student Prediction")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_feature_importance(feature_names, importances, model_name, save_path=None):
    idx = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(9, 7))
    bars = ax.barh([feature_names[i] for i in idx], importances[idx],
                   color="steelblue", edgecolor="white")
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    ax.set_xlabel("Importance Score")
    ax.set_title(f"Feature Importances -- {model_name}")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
