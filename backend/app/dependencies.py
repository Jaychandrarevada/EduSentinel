"""
FastAPI dependency injection functions.

Public API
──────────
  get_db()                  → AsyncSession
  get_current_user()        → User   (raises 401 if unauthenticated)
  require_role(*roles)      → User   (raises 403 if wrong role)
  get_student_scope()       → Optional[frozenset[int]]
                              None       = ADMIN (see every student)
                              frozenset  = FACULTY (only their enrolled students)
  assert_student_access()   → (helper) raises 403 if student outside scope

Usage examples
──────────────
  # Any authenticated user:
  user: User = Depends(get_current_user)

  # Admin-only:
  user: User = Depends(require_role(Role.ADMIN))

  # Admin or Faculty:
  user: User = Depends(require_role(Role.ADMIN, Role.FACULTY))

  # Faculty-scoped student list:
  scope = Depends(get_student_scope)
  assert_student_access(student_id, scope)   # raises 403 if outside scope
"""
from __future__ import annotations

import structlog
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models.user import User, Role
from app.services.user_service import get_user_by_id

log = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Database session ──────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional async DB session.
    Commits on success, rolls back on any exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated User. Raises 401 on failure."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exc

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    return user


# ── Role-based access control ─────────────────────────────────────────────────

def require_role(*roles: Role):
    """
    Dependency factory — restricts endpoint access to specific roles.

    Raises HTTP 403 if the authenticated user's role is not in `roles`.

    Example:
        current_user: User = Depends(require_role(Role.ADMIN))
        current_user: User = Depends(require_role(Role.ADMIN, Role.FACULTY))
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            role_names = [r.value for r in roles]
            log.warning(
                "auth.access_denied",
                user_id=current_user.id,
                required_roles=role_names,
                user_role=current_user.role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to: {', '.join(role_names)}",
            )
        return current_user

    return _check


# ── Faculty data-scoping ──────────────────────────────────────────────────────

async def _fetch_faculty_student_ids(db: AsyncSession, faculty_id: int) -> list[int]:
    """
    Return the IDs of all students enrolled in any course taught by `faculty_id`.

    SQL equivalent:
        SELECT DISTINCT e.student_id
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE c.faculty_id = :faculty_id
    """
    # Imported here to avoid circular imports at module load
    from app.models.enrollment import Enrollment
    from app.models.course import Course

    result = await db.execute(
        select(Enrollment.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )
    return [row[0] for row in result.all()]


async def get_student_scope(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[frozenset[int]]:
    """
    Resolve the data scope for the current user.

    Returns:
        None             — ADMIN: unrestricted access to all students.
        frozenset[int]   — FACULTY: IDs of students enrolled in their courses.
                           Empty frozenset if no students are assigned yet.

    Typical usage in a list endpoint:
        scope: Optional[frozenset[int]] = Depends(get_student_scope)
        # then filter queries by scope when scope is not None

    Typical usage in a per-student endpoint:
        scope: Optional[frozenset[int]] = Depends(get_student_scope)
        assert_student_access(student_id, scope)
    """
    if current_user.role == Role.ADMIN:
        return None  # full access — no filter needed

    ids = await _fetch_faculty_student_ids(db, current_user.id)
    return frozenset(ids)


def assert_student_access(
    student_id: int,
    scope: Optional[frozenset[int]],
) -> None:
    """
    Raise HTTP 403 if a faculty member attempts to access a student who is not
    enrolled in any of their courses.

    This is a plain function (not a Depends). Call it at the start of any
    per-student endpoint that uses `scope = Depends(get_student_scope)`.

    No-op when scope is None (i.e. current user is ADMIN).
    """
    if scope is not None and student_id not in scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this student is not assigned to your courses.",
        )
