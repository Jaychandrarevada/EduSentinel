"""Health check endpoints for ML service."""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health/live")
async def liveness():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request):
    pipeline_loaded = request.app.state.pipeline is not None
    meta = request.app.state.model_meta or {}
    return {
        "status": "ready" if pipeline_loaded else "degraded",
        "model_loaded": pipeline_loaded,
        "version": meta.get("version"),
        "model_name": meta.get("model_name"),
    }
