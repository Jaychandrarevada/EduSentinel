"""Celery alert tasks – stub."""
from app.workers.celery_app import celery_app

@celery_app.task(name="app.workers.alert_tasks.check_and_create_alerts")
def check_and_create_alerts():
    pass
