"""
Auth router — register, login, token refresh, profile.

RBAC
────
  POST /auth/register        ADMIN only (except in development mode, where it is open
                             to allow bootstrapping the first admin account).
  POST /auth/login           Public (rate-limited: 10/minute).
  POST /auth/refresh         Public (requires valid refresh token).
  GET  /auth/me              Any authenticated user.
  POST /auth/change-password Any authenticated user (for themselves).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.dependencies import get_db, get_current_user, require_role
from app.models.user import Role, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service
from app.core.security import hash_password, verify_password
from app.core.exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/faculty-register", response_model=TokenResponse, status_code=201)
async def faculty_register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public self-registration for faculty members.
    Always creates a FACULTY-role account — cannot be used to create admins.
    Issues access + refresh tokens on success so the user is immediately logged in.
    """
    from app.services.user_service import get_user_by_email

    # Force role to FACULTY regardless of what the payload says
    payload = payload.model_copy(update={"role": "FACULTY"})

    # Check for existing email up-front to give a clean error
    if await get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = await auth_service.register_user(db, payload)

    # Issue tokens so the user lands straight in the dashboard
    from app.core.security import create_access_token, create_refresh_token
    from app.config import settings as s

    # user is a UserOut Pydantic model — role is already a plain string
    access_token = create_access_token(
        user.id, extra_claims={"role": user.role, "email": user.email}
    )
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user (Admin or Faculty).

    - In **development** mode this endpoint is open so you can bootstrap
      the first admin account without needing an existing token.
    - In **production** (`APP_ENV=production`) the caller must be an
      authenticated ADMIN. The token is validated here directly so we can
      keep a single endpoint rather than duplicating the route.
    """
    if settings.APP_ENV == "production":
        # Enforce admin auth in production
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to register new users in production.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        from app.core.security import decode_access_token
        from app.services.user_service import get_user_by_id

        token_payload = decode_access_token(auth_header[len("Bearer "):])
        if not token_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        caller = await get_user_by_id(db, int(token_payload["sub"]))
        if not caller or not caller.is_active or caller.role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can register new users.",
            )

    return await auth_service.register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate and return access + refresh tokens.
    Rate-limited to 10 attempts per minute per IP.
    """
    return await auth_service.login_user(db, payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Issue a new token pair given a valid refresh token."""
    return await auth_service.refresh_tokens(db, payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserOut.model_validate(current_user)


@router.post("/change-password", status_code=204)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the current user's own password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise AuthenticationError("Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()
