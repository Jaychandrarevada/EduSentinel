"""Celery tasks: periodic ML prediction jobs."""
import httpx
from app.workers.celery_app import celery_app
from app.config import settings


@celery_app.task(name="app.workers.prediction_tasks.run_weekly_predictions", bind=True, max_retries=3)
def run_weekly_predictions(self, semester: str | None = None):
    """Trigger ML batch prediction for the current semester."""
    try:
        with httpx.Client(timeout=300) as client:
            resp = client.post(
                f"{settings.ML_SERVICE_URL}/predict/batch",
                json={"semester": semester or "current"},
            )
            resp.raise_for_status()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)
