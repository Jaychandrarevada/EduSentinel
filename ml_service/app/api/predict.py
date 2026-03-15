"""ML prediction API endpoints."""
import pandas as pd
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Request, status

from app.pipeline.data_loader import DataLoader
from app.pipeline.predictor import predict_batch, predict_single
from app.schemas.prediction import (
    BatchPredictRequest,
    BatchPredictResponse,
    SinglePredictRequest,
    StudentPrediction,
    ModelInfoResponse,
)

router = APIRouter()


def _get_model_and_meta(request: Request):
    """Extract loaded pipeline and metadata from app state."""
    pipeline = request.app.state.pipeline
    metadata = request.app.state.model_meta
    if pipeline is None or metadata is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No production model loaded. Run POST /train first.",
        )
    return pipeline, metadata


@router.get("/model-info", response_model=ModelInfoResponse)
async def model_info(request: Request):
    """Return metadata about the currently loaded production model."""
    pipeline = request.app.state.pipeline
    metadata = request.app.state.model_meta
    if pipeline is None or metadata is None:
        return ModelInfoResponse(status="no_model_loaded")
    return ModelInfoResponse(
        status="loaded",
        version=metadata.get("version"),
        model_name=metadata.get("model_name"),
        threshold=metadata.get("threshold"),
        metrics=metadata.get("metrics"),
        feature_cols=metadata.get("feature_cols"),
        created_at=metadata.get("created_at"),
    )


@router.post("/single", response_model=StudentPrediction)
async def single_predict(payload: SinglePredictRequest, request: Request):
    """
    Predict risk for a single student given their feature values.
    Called by the backend when a student's profile is updated.
    """
    pipeline, metadata = _get_model_and_meta(request)

    raw_features = payload.model_dump(exclude={"student_id"})
    result = predict_single(
        pipeline=pipeline,
        raw_features=raw_features,
        threshold=metadata.get("threshold", 0.5),
    )
    return StudentPrediction(student_id=payload.student_id, **result)


@router.post("/batch", response_model=BatchPredictResponse)
async def batch_predict(payload: BatchPredictRequest, request: Request):
    """
    Run at-risk prediction for all students in a semester.
    Called by the backend (Celery task or direct HTTP).
    """
    pipeline, metadata = _get_model_and_meta(request)

    try:
        from app.pipeline.data_loader import DataLoader
        loader = DataLoader()
        start_date = str(date.today() - timedelta(weeks=payload.lookback_weeks))
        raw_df = await loader.load_from_db(
            semester=payload.semester,
            start_date=start_date,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load feature data: {exc}",
        )

    if raw_df.empty:
        return BatchPredictResponse(
            semester=payload.semester,
            predictions=[],
            total=0,
        )

    predictions = predict_batch(
        pipeline=pipeline,
        feature_df=raw_df,
        threshold=metadata.get("threshold", 0.5),
    )

    return BatchPredictResponse(
        semester=payload.semester,
        predictions=[StudentPrediction(**p) for p in predictions],
        total=len(predictions),
    )
