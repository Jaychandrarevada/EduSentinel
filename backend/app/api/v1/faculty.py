"""
Faculty router
══════════════
Two logical sections in one router:

  Admin section  (prefix /faculty, require_role ADMIN)
  ─────────────────────────────────────────────────────
  GET    /faculty                   List all faculty (search, dept, active filters)
  GET    /faculty/{id}              Faculty profile + stats
  PATCH  /faculty/{id}              Update profile (name, email, department)
  POST   /faculty/{id}/deactivate   Deactivate account
  POST   /faculty/{id}/activate     Re-activate account
  GET    /faculty/{id}/students     Students assigned to this faculty member
  GET    /faculty/{id}/courses      Courses taught by this faculty member

  Faculty self-service  (prefix /faculty/me, require_role FACULTY)
  ─────────────────────────────────────────────────────────────────
  GET    /faculty/me                My profile + stats
  GET    /faculty/me/students       My assigned students (searchable, paginated)
  GET    /faculty/me/courses        My courses
  GET    /faculty/me/alerts         At-risk alerts for my students
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.user import Role, User
from app.schemas.common import PaginatedResponse
from app.schemas.faculty import FacultyActivateRequest, FacultyOut, FacultyUpdate, FacultyWithStats
from app.schemas.prediction import AlertOut
from app.schemas.student import StudentOut
from app.services import faculty_service

router = APIRouter(prefix="/faculty", tags=["Faculty Management"])


# ─────────────────────────────────────────────────────────────────────────────
#  Faculty self-service  (/faculty/me/*)
#  Must be declared BEFORE /{id} routes to avoid routing collision.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=FacultyWithStats)
async def my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.FACULTY)),
):
    """Return the current faculty member's profile with course/student/alert counts."""
    stats = await faculty_service.get_faculty_stats(db, current_user.id)
    return FacultyWithStats(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        department=current_user.department,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        **stats,
    )


@router.get("/me/students", response_model=PaginatedResponse[StudentOut])
async def my_students(
    search: Optional[str] = Query(None, max_length=100),
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=12),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.FACULTY)),
):
    """
    Return students enrolled in any of the current faculty's courses.
    Supports name/roll-no search, department, and semester filters.
    """
    students, total = await faculty_service.get_faculty_students(
        db,
        faculty_id=current_user.id,
        search=search,
        department=department,
        semester=semester,
        page=page,
        size=size,
    )
    return PaginatedResponse.build(
        items=[StudentOut.model_validate(s) for s in students],
        total=total,
        page=page,
        size=size,
    )


@router.get("/me/courses")
async def my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.FACULTY)),
):
    """Return all courses assigned to the current faculty member."""
    courses = await faculty_service.get_faculty_courses(db, current_user.id)
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "department": c.department,
            "semester": c.semester,
            "credits": c.credits,
            "academic_year": c.academic_year,
        }
        for c in courses
    ]


@router.get("/me/alerts", response_model=PaginatedResponse[AlertOut])
async def my_alerts(
    is_resolved: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.FACULTY)),
):
    """
    Return at-risk alerts for students in the current faculty's courses.
    Defaults to unresolved alerts — pass ?is_resolved=true for history.
    """
    alerts, total = await faculty_service.get_faculty_alerts(
        db,
        faculty_id=current_user.id,
        is_resolved=is_resolved,
        page=page,
        size=size,
    )
    return PaginatedResponse.build(
        items=[AlertOut.model_validate(a) for a in alerts],
        total=total,
        page=page,
        size=size,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Admin: faculty management  (/faculty, /faculty/{id}/*)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[FacultyWithStats])
async def list_faculty(
    search: Optional[str] = Query(None, max_length=100),
    department: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """
    List all faculty members with stats.
    Supports name/email search, department filter, and active-status filter.
    """
    users, total = await faculty_service.list_faculty(
        db,
        search=search,
        department=department,
        is_active=is_active,
        page=page,
        size=size,
    )

    items = []
    for u in users:
        stats = await faculty_service.get_faculty_stats(db, u.id)
        items.append(
            FacultyWithStats(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                department=u.department,
                is_active=u.is_active,
                created_at=u.created_at,
                **stats,
            )
        )

    return PaginatedResponse.build(items=items, total=total, page=page, size=size)


@router.get("/{faculty_id}", response_model=FacultyWithStats)
async def get_faculty(
    faculty_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Return a faculty member's full profile with stats. Admin only."""
    faculty = await faculty_service.get_faculty_or_404(db, faculty_id)
    stats = await faculty_service.get_faculty_stats(db, faculty_id)
    return FacultyWithStats(
        id=faculty.id,
        email=faculty.email,
        full_name=faculty.full_name,
        department=faculty.department,
        is_active=faculty.is_active,
        created_at=faculty.created_at,
        **stats,
    )


@router.patch("/{faculty_id}", response_model=FacultyOut)
async def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """Update a faculty member's name, email, or department. Admin only."""
    faculty = await faculty_service.update_faculty(db, faculty_id, payload)
    return FacultyOut.model_validate(faculty)


@router.post("/{faculty_id}/deactivate", response_model=FacultyOut)
async def deactivate_faculty(
    faculty_id: int,
    payload: FacultyActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    Deactivate a faculty account — they can no longer log in.
    Admin only. Cannot deactivate yourself.
    """
    faculty = await faculty_service.set_faculty_active(
        db,
        faculty_id=faculty_id,
        active=False,
        requested_by=current_user.id,
    )
    return FacultyOut.model_validate(faculty)


@router.post("/{faculty_id}/activate", response_model=FacultyOut)
async def activate_faculty(
    faculty_id: int,
    payload: FacultyActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Re-activate a previously deactivated faculty account. Admin only."""
    faculty = await faculty_service.set_faculty_active(
        db,
        faculty_id=faculty_id,
        active=True,
        requested_by=current_user.id,
    )
    return FacultyOut.model_validate(faculty)


@router.get("/{faculty_id}/students", response_model=PaginatedResponse[StudentOut])
async def faculty_students(
    faculty_id: int,
    search: Optional[str] = Query(None, max_length=100),
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=12),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """List students assigned to a specific faculty member. Admin only."""
    students, total = await faculty_service.get_faculty_students(
        db,
        faculty_id=faculty_id,
        search=search,
        department=department,
        semester=semester,
        page=page,
        size=size,
    )
    return PaginatedResponse.build(
        items=[StudentOut.model_validate(s) for s in students],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{faculty_id}/courses")
async def faculty_courses(
    faculty_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(Role.ADMIN)),
):
    """List courses assigned to a specific faculty member. Admin only."""
    courses = await faculty_service.get_faculty_courses(db, faculty_id)
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "department": c.department,
            "semester": c.semester,
            "credits": c.credits,
            "academic_year": c.academic_year,
        }
        for c in courses
    ]
