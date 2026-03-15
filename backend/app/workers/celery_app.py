"""Celery application and periodic task schedule."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "edusentinel",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.prediction_tasks", "app.workers.alert_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Run predictions every Sunday at 2 AM UTC
    "weekly-prediction-refresh": {
        "task": "app.workers.prediction_tasks.run_weekly_predictions",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    # Check for new alerts every hour
    "hourly-alert-check": {
        "task": "app.workers.alert_tasks.check_and_create_alerts",
        "schedule": crontab(minute=0),
    },
}
