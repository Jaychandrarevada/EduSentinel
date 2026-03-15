"""
Prediction service — calls ML microservice and persists results.
Also manages alert creation based on risk levels.
"""
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.prediction import Prediction, RiskLabel
from app.schemas.prediction import PredictionOut, PredictionRunResponse, RiskPredictRequest, RiskPredictResponse

log = structlog.get_logger()


async def get_predictions(
    db: AsyncSession,
    risk_label: Optional[str] = None,
    semester: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    student_ids: Optional[list[int]] = None,  # faculty scope
) -> tuple[list[PredictionOut], int]:
    q = select(Prediction)
    if student_ids is not None:
        q = q.where(Prediction.student_id.in_(student_ids))
    if risk_label:
        q = q.where(Prediction.risk_label == risk_label.upper())
    if semester:
        q = q.where(Prediction.semester == semester)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    predictions = (
        await db.execute(q.offset((page - 1) * size).limit(size))
    ).scalars().all()
    return [PredictionOut.model_validate(p) for p in predictions], total


async def get_prediction_summary(
    db: AsyncSession,
    semester: Optional[str] = None,
    student_ids: Optional[list[int]] = None,  # faculty scope
) -> dict:
    q = select(Prediction.risk_label, func.count().label("count"))
    if student_ids is not None:
        q = q.where(Prediction.student_id.in_(student_ids))
    if semester:
        q = q.where(Prediction.semester == semester)
    q = q.group_by(Prediction.risk_label)
    rows = (await db.execute(q)).all()

    counts: dict = {r.risk_label: r.count for r in rows}
    total = sum(counts.values())
    high = counts.get(RiskLabel.HIGH, 0)

    last_run_q = select(func.max(Prediction.predicted_at))
    if student_ids is not None:
        last_run_q = last_run_q.where(Prediction.student_id.in_(student_ids))
    if semester:
        last_run_q = last_run_q.where(Prediction.semester == semester)
    last_run = (await db.execute(last_run_q)).scalar_one_or_none()

    return {
        "total_students": total,
        "high_risk_count": high,
        "medium_risk_count": counts.get(RiskLabel.MEDIUM, 0),
        "low_risk_count": counts.get(RiskLabel.LOW, 0),
        "high_risk_pct": round((high / total * 100) if total else 0, 1),
        "last_run_at": last_run,
    }


async def trigger_prediction_run(
    db: AsyncSession,
    semester: str,
    requested_by: int,
) -> PredictionRunResponse:
    """Call ML service /predict/batch, persist results, and create alerts."""
    try:
        async with httpx.AsyncClient(timeout=settings.ML_REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/predict/batch",
                json={"semester": semester},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        log.error("ml_service.http_error", status=exc.response.status_code)
        raise ServiceUnavailableError("ML service returned an error")
    except httpx.RequestError as exc:
        log.error("ml_service.connection_error", error=str(exc))
        raise ServiceUnavailableError("ML service is unreachable")

    predictions = data.get("predictions", [])
    inserted = 0

    for pred in predictions:
        record = Prediction(
            student_id=pred["student_id"],
            semester=semester,
            risk_score=pred["risk_score"],
            risk_label=RiskLabel(pred["risk_label"]),
            contributing_factors=pred.get("contributing_factors"),
            model_version=data.get("model_version", "unknown"),
            predicted_at=datetime.now(timezone.utc),
        )
        db.add(record)

        # Auto-create HIGH risk alerts
        if pred["risk_label"] == "HIGH":
            alert = Alert(
                student_id=pred["student_id"],
                alert_type=AlertType.HIGH_RISK_PREDICTED,
                severity=AlertSeverity.HIGH,
                message=(
                    f"Student predicted HIGH risk (score: {pred['risk_score']:.2%}) "
                    f"in semester {semester}. "
                    f"Top factor: {pred['contributing_factors'][0]['feature'] if pred.get('contributing_factors') else 'N/A'}"
                ),
            )
            db.add(alert)

        inserted += 1

    await db.commit()
    log.info("prediction.run_complete", semester=semester, inserted=inserted)
    return PredictionRunResponse(
        message=f"Prediction run complete. {inserted} students scored.",
        semester=semester,
    )


_RECOMMENDATIONS = {
    "HIGH":   "Faculty intervention recommended",
    "MEDIUM": "Monitor student progress closely",
    "LOW":    "Student is performing well",
}


async def predict_risk_quick(payload: RiskPredictRequest) -> RiskPredictResponse:
    """
    Call ML service /predict/single with simplified inputs.

    Maps the 6-field public request to the ML service's raw feature format,
    then returns a simplified risk level + recommendation.
    """
    # lms_activity (0–100%) → approximate logins/week and content views
    logins_per_week = round(payload.lms_activity / 100 * 7, 2)
    content_views   = round(payload.lms_activity / 100 * 50, 2)

    ml_payload = {
        "student_id": 0,                            # ad-hoc; not persisted
        "attendance_pct":            payload.attendance,
        "ia1_score":                 payload.internal_score,
        "ia2_score":                 payload.internal_score,
        "ia3_score":                 payload.internal_score,
        "assignment_avg_score":      payload.assignment_score,
        "assignment_completion_rate": round(payload.assignment_score / 100, 4),
        "lms_login_frequency":       logins_per_week,
        "lms_time_spent_hours":      payload.engagement_time,
        "lms_content_views":         content_views,
        "previous_gpa":              payload.previous_gpa,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/predict/single",
                json=ml_payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        log.error("ml_service.predict_risk.http_error", status=exc.response.status_code)
        raise ServiceUnavailableError("ML service returned an error")
    except httpx.RequestError as exc:
        log.error("ml_service.predict_risk.connection_error", error=str(exc))
        raise ServiceUnavailableError("ML service is unreachable")

    risk_label = data["risk_label"]          # "HIGH" | "MEDIUM" | "LOW"
    probability = round(data["risk_score"], 4)

    return RiskPredictResponse(
        risk_level=risk_label.capitalize(),  # "High" | "Medium" | "Low"
        probability=probability,
        recommendation=_RECOMMENDATIONS.get(risk_label, "No recommendation available"),
    )


async def resolve_alert(
    db: AsyncSession, alert_id: int, resolved_by: int
) -> None:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Alert", alert_id)
    alert.is_resolved = True
    alert.resolved_by = resolved_by
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
