"""
EduSentinel – FastAPI application entry point.

Startup sequence:
  1. Setup structured logging
  2. Create DB tables (dev only — use Alembic in production)
  3. Register all routers under /api/v1
  4. Register exception handlers
  5. Add CORS, rate-limiting, and request-logging middleware
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.database import engine, Base
from app.middleware import RequestLogMiddleware

setup_logging(debug=settings.DEBUG)
log = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    log.info(
        "app.startup",
        env=settings.APP_ENV,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # In development, auto-create tables.
    # In production, use: alembic upgrade head
    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            import app.models  # noqa: F401  — ensures all models are registered
            await conn.run_sync(Base.metadata.create_all)
        log.info("app.db_tables_ensured")

    yield

    await engine.dispose()
    log.info("app.shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Learning Analytics-Based Student Performance Monitoring System.\n\n"
        "Provides REST APIs for student data ingestion, ML-powered at-risk predictions, "
        "and dashboards for faculty and administrators."
    ),
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware (order matters: outermost runs first) ──────────────────────────

# 1. Request / audit logging — must wrap everything so latency is accurate
app.add_middleware(RequestLogMiddleware)

# 2. Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Health checks ─────────────────────────────────────────────────────────────
@app.get("/health/live", tags=["Health"], include_in_schema=False)
async def liveness():
    """Kubernetes liveness probe — is the process running?"""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    """Kubernetes readiness probe — is the app ready to serve traffic?"""
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    ready = db_status == "ok"
    return {
        "status": "ready" if ready else "degraded",
        "database": db_status,
    }


@app.get("/system-health", tags=["Health"])
async def system_health():
    """
    Comprehensive system health check.
    Returns status of: database, ML model registry, API, and key feature flags.
    """
    import httpx
    from sqlalchemy import text, func, select
    from datetime import timezone

    checks: dict = {}

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        # Count key entities
        from app.database import AsyncSessionLocal
        from app.models.student import Student
        from app.models.user import User
        from app.models.prediction import Prediction

        async with AsyncSessionLocal() as db:
            student_count = (await db.execute(select(func.count(Student.id)))).scalar_one()
            user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
            prediction_count = (await db.execute(select(func.count(Prediction.id)))).scalar_one()

        checks["database"] = {
            "status": "ok",
            "students": student_count,
            "users": user_count,
            "predictions": prediction_count,
        }
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}

    # ── ML Service ────────────────────────────────────────────────────────────
    ml_url = settings.ML_SERVICE_URL
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{ml_url}/health")
        checks["ml_service"] = {
            "status": "ok" if resp.status_code == 200 else "degraded",
            "url": ml_url,
        }
    except Exception:
        checks["ml_service"] = {
            "status": "unavailable",
            "url": ml_url,
            "note": "ML service not running — predictions use cached results",
        }

    # ── API ───────────────────────────────────────────────────────────────────
    checks["api"] = {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "debug_mode": settings.DEBUG,
    }

    # ── Feature flags ─────────────────────────────────────────────────────────
    checks["features"] = {
        "email_notifications": bool(
            getattr(settings, "NOTIFICATION_ENABLED", False)
        ),
        "csv_export": True,
        "shap_explainability": True,
        "data_generator": True,
    }

    # ── Overall status ────────────────────────────────────────────────────────
    critical_ok = checks["database"]["status"] == "ok" and checks["api"]["status"] == "ok"
    overall = "healthy" if critical_ok else "degraded"

    return {
        "status": overall,
        "timestamp": __import__("datetime").datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
