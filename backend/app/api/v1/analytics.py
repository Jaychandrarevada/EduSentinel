"""
Analytics router — cohort-level dashboard KPIs.

RBAC
────
  All endpoints: ADMIN only.
  Faculty dashboards use /faculty/me/students and /predictions instead.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.user import Role, User
from app.schemas.analytics import CohortOverview, DepartmentStat
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/cohort-overview", response_model=CohortOverview)
async def cohort_overview(
    semester: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """
    Top-level cohort statistics for the admin dashboard:
    total students, risk breakdown, avg attendance, avg marks, alert count.
    Admin only.
    """
    return await analytics_service.get_cohort_overview(db, semester)


@router.get("/departments", response_model=list[DepartmentStat])
async def department_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Per-department breakdown of attendance, marks, and at-risk counts. Admin only."""
    return await analytics_service.get_department_stats(db)
