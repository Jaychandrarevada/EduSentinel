"""ML Service – FastAPI entry point."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, predict, train
from app.registry.model_registry import ModelRegistry

log = structlog.get_logger()
registry = ModelRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("ml_service.startup", msg="Loading production model from registry")
    app.state.pipeline = None
    app.state.model_meta = None

    result = registry.load_latest()
    if result is not None:
        pipeline, metadata = result
        app.state.pipeline = pipeline
        app.state.model_meta = metadata
        log.info(
            "ml_service.model_loaded",
            version=metadata.get("version"),
            model_name=metadata.get("model_name"),
        )
    else:
        log.warning(
            "ml_service.no_model",
            msg="No production model found. POST /train to create one.",
        )

    yield

    log.info("ml_service.shutdown")


app = FastAPI(
    title="EduSentinel ML Service",
    version="1.0.0",
    description="At-risk student prediction service with SHAP explanations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(predict.router, prefix="/predict", tags=["Predict"])
app.include_router(train.router, prefix="/train", tags=["Train"])
