"""
Alerts router — faculty-facing risk alerts.

Endpoints
─────────
  GET  /alerts                    List unresolved alerts (faculty-scoped).
  POST /alerts/{id}/resolve       Mark an alert as resolved.
  POST /alerts/send-emails        Send risk alert emails to HIGH-risk students.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_student_scope, require_role
from app.models.alert import Alert, AlertSeverity
from app.models.prediction import Prediction, RiskLabel
from app.models.student import Student
from app.models.user import Role, User
from app.services import notification_service
from app.services.prediction_service import resolve_alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ── schemas ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    created_at: str

    model_config = {"from_attributes": True}


class SendEmailsRequest(BaseModel):
    semester: Optional[str] = Field(None, description="Filter by semester, e.g. '2025-ODD'")
    risk_label: str = Field("HIGH", pattern="^(HIGH|MEDIUM|LOW)$")
    dry_run: bool = Field(False, description="If true, return the list without actually sending")


class SendEmailsResponse(BaseModel):
    attempted: int
    sent: int
    skipped: int
    dry_run: bool
    students: list[dict]


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[AlertOut])
async def list_alerts(
    severity: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    unresolved_only: bool = Query(True),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    List alerts. Faculty see only alerts for their enrolled students.
    Admin sees all alerts.
    """
    q = select(Alert, Student.full_name).join(Student, Alert.student_id == Student.id)

    if scope is not None:
        q = q.where(Alert.student_id.in_(list(scope)))
    if unresolved_only:
        q = q.where(Alert.is_resolved == False)  # noqa: E712
    if severity:
        q = q.where(Alert.severity == severity.upper())

    q = q.order_by(Alert.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(q)).all()

    result = []
    for alert, student_name in rows:
        result.append(AlertOut(
            id=alert.id,
            student_id=alert.student_id,
            student_name=student_name,
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            is_resolved=alert.is_resolved,
            created_at=alert.created_at.isoformat(),
        ))
    return result


@router.post("/{alert_id}/resolve", status_code=200)
async def mark_alert_resolved(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
):
    """Mark a specific alert as resolved."""
    await resolve_alert(db, alert_id, resolved_by=current_user.id)
    return {"message": f"Alert {alert_id} resolved", "resolved_by": current_user.id}


@router.post("/send-emails", response_model=SendEmailsResponse)
async def send_risk_emails(
    payload: SendEmailsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY)),
    scope: Optional[frozenset] = Depends(get_student_scope),
):
    """
    Send risk alert emails to students matching the given risk level.

    - Fetches the latest prediction for each student in scope.
    - Sends an HTML email to each qualifying student.
    - Returns counts of sent / skipped / attempted.

    Requires NOTIFICATION_ENABLED=true and SMTP_* settings in environment.
    Use dry_run=true to preview the list without sending.
    """
    # Fetch latest predictions for risk_label
    from sqlalchemy import func
    pred_sub = (
        select(
            Prediction.student_id,
            func.max(Prediction.predicted_at).label("latest_at"),
        )
        .group_by(Prediction.student_id)
        .subquery()
    )
    q = (
        select(Prediction, Student.full_name, Student.email)
        .join(pred_sub, (Prediction.student_id == pred_sub.c.student_id) & (Prediction.predicted_at == pred_sub.c.latest_at))
        .join(Student, Prediction.student_id == Student.id)
        .where(Prediction.risk_label == RiskLabel(payload.risk_label))
    )

    if scope is not None:
        q = q.where(Prediction.student_id.in_(list(scope)))
    if payload.semester:
        q = q.where(Prediction.semester == payload.semester)

    rows = (await db.execute(q)).all()

    students_list = [
        {
            "student_name":        student_name,
            "student_email":       student_email,
            "risk_score":          pred.risk_score,
            "risk_label":          pred.risk_label,
            "contributing_factors": pred.contributing_factors or [],
            "semester":            pred.semester,
        }
        for pred, student_name, student_email in rows
    ]

    if payload.dry_run:
        return SendEmailsResponse(
            attempted=len(students_list),
            sent=0,
            skipped=len(students_list),
            dry_run=True,
            students=students_list,
        )

    sent = await notification_service.send_risk_alerts_batch(students_list)
    skipped = len(students_list) - sent

    return SendEmailsResponse(
        attempted=len(students_list),
        sent=sent,
        skipped=skipped,
        dry_run=False,
        students=students_list,
    )
