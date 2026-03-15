"""
Predictions router — trigger ML runs, fetch results, manage alerts.

RBAC
────
  GET  /predictions          Both roles. Faculty scoped to their students.
  GET  /predictions/summary  Both roles. Faculty scoped to their students.
  POST /predictions/run      ADMIN only.
  POST /predictions/predict-risk  Both roles.
  GET  /predictions/alerts   Both roles. Faculty scoped to their students.
  PATCH /predictions/alerts/{id}/resolve  Both roles; faculty restricted to their students.
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    assert_student_access,
    get_current_user,
    get_db,
    get_student_scope,
    require_role,
)
from app.models.alert import Alert
from app.models.prediction import Prediction
from app.models.user import Role, User
from app.schemas.common import PaginatedResponse
from app.schemas.prediction import (
    AlertOut,
    AlertResolveRequest,
    PredictionOut,
    PredictionRunRequest,
    PredictionRunResponse,
    RiskPredictRequest,
    RiskPredictResponse,
)
from app.services import prediction_service

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("", response_model=PaginatedResponse[PredictionOut])
async def list_predictions(
    semester: Optional[str] = Query(None),
    risk_label: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Retrieve latest predictions, filterable by semester and risk level.
    Faculty see only predictions for their assigned students.
    """
    student_ids = list(scope) if scope is not None else None

    items, total = await prediction_service.get_predictions(
        db,
        risk_label=risk_label,
        semester=semester,
        page=page,
        size=size,
        student_ids=student_ids,
    )
    return PaginatedResponse.build(items=items, total=total, page=page, size=size)


@router.get("/summary")
async def prediction_summary(
    semester: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Risk distribution counts + last run timestamp for dashboard KPIs.
    Faculty see summary scoped to their students only.
    """
    student_ids = list(scope) if scope is not None else None
    return await prediction_service.get_prediction_summary(
        db, semester=semester, student_ids=student_ids
    )


@router.post("/run", response_model=PredictionRunResponse, status_code=202)
async def run_predictions(
    payload: PredictionRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    Trigger a full ML prediction run for a semester.
    Runs in the background. Results are persisted to the predictions table.
    Admin only.
    """
    background_tasks.add_task(
        prediction_service.trigger_prediction_run,
        db,
        payload.semester,
        current_user.id,
    )
    return PredictionRunResponse(
        message="Prediction job queued successfully",
        semester=payload.semester,
    )


@router.post("/predict-risk", response_model=RiskPredictResponse)
async def predict_risk(
    payload: RiskPredictRequest,
    _: User = Depends(get_current_user),
):
    """
    Predict at-risk level for a student given academic indicators.
    Calls the ML service synchronously — no database writes.
    Available to both roles.
    """
    return await prediction_service.predict_risk_quick(payload)


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=PaginatedResponse[AlertOut])
async def list_alerts(
    severity: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    is_resolved: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Fetch alerts for the dashboard alert feed.
    Faculty see only alerts for their assigned students.
    """
    q = select(Alert).where(Alert.is_resolved == is_resolved)

    # Faculty scope
    if scope is not None:
        q = q.where(Alert.student_id.in_(list(scope)))

    if severity:
        q = q.where(Alert.severity == severity.upper())

    q = q.order_by(Alert.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    alerts = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()

    return PaginatedResponse.build(
        items=[AlertOut.model_validate(a) for a in alerts],
        total=total,
        page=page,
        size=size,
    )


@router.patch("/alerts/{alert_id}/resolve", status_code=204)
async def resolve_alert(
    alert_id: int,
    payload: AlertResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Mark an alert as resolved.
    Faculty can only resolve alerts for their own students.
    """
    # Verify faculty access to this alert's student
    result = await db.execute(select(Alert.student_id).where(Alert.id == alert_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    assert_student_access(row, scope)
    await prediction_service.resolve_alert(db, alert_id, resolved_by=current_user.id)
