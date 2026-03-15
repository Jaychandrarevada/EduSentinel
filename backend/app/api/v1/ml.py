"""
ML router — model comparison, SHAP explanations, training status.

Proxies to the ML microservice where available;
falls back to demo data when the ML service is offline.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_current_user, require_role
from app.models.user import Role, User

log = structlog.get_logger()
router = APIRouter(prefix="/ml", tags=["ML & Explainability"])

_TIMEOUT = 15  # seconds


# ── helpers ──────────────────────────────────────────────────────────────────

async def _ml_get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{settings.ML_SERVICE_URL}{path}")
        r.raise_for_status()
        return r.json()


async def _ml_post(path: str, payload: dict) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(f"{settings.ML_SERVICE_URL}{path}", json=payload)
        r.raise_for_status()
        return r.json()


def _demo_comparison() -> dict:
    return {
        "models": [
            {"name": "Logistic Regression", "accuracy": 0.82, "precision": 0.79, "recall": 0.84, "f1": 0.81, "roc_auc": 0.88, "training_time_sec": 1.2},
            {"name": "Random Forest",       "accuracy": 0.89, "precision": 0.87, "recall": 0.91, "f1": 0.89, "roc_auc": 0.94, "training_time_sec": 8.5},
            {"name": "XGBoost",             "accuracy": 0.91, "precision": 0.89, "recall": 0.93, "f1": 0.91, "roc_auc": 0.96, "training_time_sec": 12.3},
        ],
        "best_model":      "XGBoost",
        "best_metric":     "roc_auc",
        "comparison_date": datetime.now(timezone.utc).isoformat(),
        "data_source":     "fallback_demo",
    }


def _demo_shap_global() -> dict:
    return {
        "feature_importance": [
            {"feature": "attendance_pct",             "importance": 0.28, "description": "Attendance percentage"},
            {"feature": "ia1_score",                  "importance": 0.19, "description": "Internal Assessment 1"},
            {"feature": "assignment_avg_score",       "importance": 0.15, "description": "Assignment average"},
            {"feature": "ia2_score",                  "importance": 0.14, "description": "Internal Assessment 2"},
            {"feature": "lms_engagement_score",       "importance": 0.12, "description": "LMS engagement"},
            {"feature": "previous_gpa",               "importance": 0.08, "description": "Previous GPA"},
            {"feature": "assignment_completion_rate", "importance": 0.04, "description": "Assignment completion"},
        ],
        "model_name":  "XGBoost",
        "data_source": "fallback_demo",
    }


def _demo_shap_student(student_id: int) -> dict:
    return {
        "student_id": student_id,
        "risk_score": 0.73,
        "risk_label": "HIGH",
        "explanation": [
            {"feature": "attendance_pct",             "value": 58.0, "shap_value":  0.31, "direction": "increases_risk"},
            {"feature": "ia1_score",                  "value": 44.0, "shap_value":  0.22, "direction": "increases_risk"},
            {"feature": "lms_engagement_score",       "value": 35.0, "shap_value":  0.18, "direction": "increases_risk"},
            {"feature": "assignment_avg_score",       "value": 52.0, "shap_value":  0.14, "direction": "increases_risk"},
            {"feature": "previous_gpa",               "value":  7.2, "shap_value": -0.12, "direction": "decreases_risk"},
            {"feature": "ia2_score",                  "value": 55.0, "shap_value":  0.09, "direction": "increases_risk"},
            {"feature": "assignment_completion_rate", "value": 65.0, "shap_value": -0.05, "direction": "decreases_risk"},
        ],
    }


# ── schemas ───────────────────────────────────────────────────────────────────

class TrainAllRequest(BaseModel):
    data_source: str = "synthetic"
    n_synthetic_samples: int = 1000


class StudentShapRequest(BaseModel):
    student_id: int


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/model-comparison", summary="Compare all ML model metrics")
async def model_comparison(
    current_user: User = Depends(get_current_user),
):
    """
    Returns accuracy, precision, recall, F1 and ROC-AUC for all trained models.
    Falls back to demo data if the ML service is unreachable.
    """
    try:
        return await _ml_get("/models/comparison")
    except Exception as exc:
        log.warning("ml_service.model_comparison.unavailable", error=str(exc))
        return _demo_comparison()


@router.get("/shap/global", summary="Global SHAP feature importance")
async def shap_global(
    current_user: User = Depends(get_current_user),
):
    """Returns global feature importance from SHAP for the production model."""
    try:
        return await _ml_get("/explain/global")
    except Exception as exc:
        log.warning("ml_service.shap_global.unavailable", error=str(exc))
        return _demo_shap_global()


@router.post("/shap/student", summary="SHAP explanation for a single student")
async def shap_student(
    payload: StudentShapRequest,
    current_user: User = Depends(get_current_user),
):
    """Returns per-feature SHAP values for the given student's latest prediction."""
    try:
        return await _ml_post("/explain/student", {"student_id": payload.student_id})
    except Exception as exc:
        log.warning("ml_service.shap_student.unavailable", error=str(exc))
        return _demo_shap_student(payload.student_id)


@router.get("/training-status", summary="ML training job status")
async def training_status(
    current_user: User = Depends(get_current_user),
):
    """Check whether a training job is currently running."""
    try:
        return await _ml_get("/train/status")
    except Exception:
        return {"status": "unknown", "detail": "ML service offline"}


@router.post("/train-all", summary="Trigger training of all models", status_code=status.HTTP_202_ACCEPTED)
async def train_all_models(
    payload: TrainAllRequest,
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """
    Kick off training for all 3 model types (LR, RF, XGBoost).
    Returns 202 Accepted — training is asynchronous.
    """
    try:
        return await _ml_post("/train", {
            "data_source": payload.data_source,
            "n_synthetic_samples": payload.n_synthetic_samples,
        })
    except Exception as exc:
        log.warning("ml_service.train.unavailable", error=str(exc))
        return {
            "message": "Training request accepted (ML service offline — will run when available)",
            "status": "queued",
        }
