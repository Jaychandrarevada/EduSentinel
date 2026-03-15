"""
RequestLogMiddleware
════════════════════
Starlette middleware that emits one structured log line per request.

Fields logged:
  method          HTTP verb
  path            URL path (no query string)
  status_code     Response status
  latency_ms      End-to-end latency in milliseconds
  user_id         Decoded from Bearer JWT (or null for anonymous)
  role            User role extracted from JWT claims (or null)
  ip              Client IP (respects X-Forwarded-For)

All fields are safe to index/search in any structured log backend
(Loki, Datadog, CloudWatch, etc.).
"""
from __future__ import annotations

import time
from typing import Optional

import structlog
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger("access")

# Import lazily to avoid circular deps at module load time
def _get_settings():
    from app.config import settings
    return settings


def _extract_jwt_claims(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract (user_id, role) from the Bearer token in the Authorization header.
    Returns (None, None) if the token is absent, invalid, or expired.
    Does NOT raise — this is best-effort for logging only.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None

    token = auth_header[len("Bearer "):]
    try:
        settings = _get_settings()
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},  # don't raise on expired; log anyway
        )
        return str(payload.get("sub")), payload.get("role")
    except JWTError:
        return None, None


def _client_ip(request: Request) -> str:
    """Return the real client IP, honouring X-Forwarded-For (set by Nginx)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RequestLogMiddleware(BaseHTTPMiddleware):
    """
    Emit one structured access-log line per HTTP request.

    Attach to the FastAPI app:
        app.add_middleware(RequestLogMiddleware)
    """

    # Paths to skip logging (liveness/readiness probes generate noise)
    _SKIP_PATHS = frozenset({"/health/live", "/health/ready"})

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        user_id, role = _extract_jwt_claims(request)
        ip = _client_ip(request)
        t0 = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            log.error(
                "request.unhandled_exception",
                method=request.method,
                path=request.url.path,
                user_id=user_id,
                role=role,
                ip=ip,
                exc=str(exc),
            )
            raise
        finally:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        level = "warning" if status_code >= 400 else "info"
        getattr(log, level)(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            latency_ms=latency_ms,
            user_id=user_id,
            role=role,
            ip=ip,
        )

        return response
