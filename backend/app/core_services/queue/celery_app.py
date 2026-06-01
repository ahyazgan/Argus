"""Celery uygulamasi - async tarama islerinin kuyrugu."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "argus",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Genel tarama gorevi app.core_services.queue.scan_tasks icinde tanimli ve
# worker.py tarafindan acikca import edilir. Ek otomatik kesif gerekmez.
