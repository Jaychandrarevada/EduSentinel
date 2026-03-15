"""
Authentication service — register, login, token management.
All business logic lives here; routers stay thin.
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.models.user import User, Role
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut
from app.services.user_service import get_user_by_email, get_user_by_id, create_user

log = structlog.get_logger()


async def register_user(db: AsyncSession, payload: RegisterRequest) -> UserOut:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise ConflictError(f"A user with email '{payload.email}' already exists")

    user = await create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=Role(payload.role),
        department=payload.department,
    )
    await db.commit()
    log.info("user.registered", user_id=user.id, role=user.role)
    return UserOut.model_validate(user)


async def login_user(db: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        log.warning("auth.login_failed", email=email)
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    access_token = create_access_token(
        subject=user.id, extra_claims={"role": user.role, "email": user.email}
    )
    refresh_token = create_refresh_token(subject=user.id)

    log.info("auth.login_success", user_id=user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_refresh_token(refresh_token)
    if not payload:
        raise AuthenticationError("Invalid or expired refresh token")

    user = await get_user_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise AuthenticationError("User not found or deactivated")

    access_token = create_access_token(
        subject=user.id, extra_claims={"role": user.role, "email": user.email}
    )
    new_refresh = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
