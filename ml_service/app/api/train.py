"""ML training trigger endpoint."""
import asyncio
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.pipeline.trainer import run_training_pipeline
from app.registry.model_registry import ModelRegistry
from app.schemas.prediction import TrainRequest, TrainResponse

log = structlog.get_logger()
router = APIRouter()
registry = ModelRegistry()

# Track whether a training job is currently running to prevent concurrent runs
_training_in_progress = False


async def _run_and_reload(app, request: TrainRequest):
    """Background task: train a new model and hot-reload it into app state."""
    global _training_in_progress
    _training_in_progress = True
    try:
        log.info("training.started", data_source=request.data_source)
        result = await asyncio.to_thread(
            run_training_pipeline,
            source=request.data_source,
            csv_path=request.csv_path,
            n_samples=request.n_synthetic_samples,
        )
        # Hot-reload the new model into the running application
        loaded = registry.load_latest()
        if loaded is not None:
            app.state.pipeline, app.state.model_meta = loaded
        log.info(
            "training.completed",
            version=result.get("version"),
            model_name=result.get("best_model"),
            roc_auc=result.get("metrics", {}).get("roc_auc"),
        )
    except Exception:
        log.exception("training.failed")
    finally:
        _training_in_progress = False


@router.post("", response_model=TrainResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_training(
    payload: TrainRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """
    Kick off a model training run in the background.

    - `data_source`: 'synthetic' (default), 'csv' (requires csv_path), or 'db' (requires semester)
    - Returns 202 immediately; training happens asynchronously.
    - The production model in app.state is hot-reloaded once training completes.
    """
    global _training_in_progress
    if _training_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A training job is already in progress.",
        )
    if payload.data_source == "csv" and not payload.csv_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="csv_path is required when data_source='csv'",
        )
    background_tasks.add_task(_run_and_reload, request.app, payload)
    return TrainResponse(
        message="Training job started. The model will be hot-reloaded upon completion.",
    )


@router.get("/status", response_model=TrainResponse)
async def training_status():
    """Check whether a training job is currently running."""
    if _training_in_progress:
        return TrainResponse(message="Training is currently in progress.")
    result = registry.load_latest()
    if result is None:
        return TrainResponse(message="No trained model found. Trigger training first.")
    _, meta = result
    return TrainResponse(
        message="No training in progress. Last trained model is the production model.",
        version=meta.get("version"),
        model_name=meta.get("model_name"),
        metrics=meta.get("metrics"),
        quality_gates_passed=meta.get("quality_gates_passed"),
    )
