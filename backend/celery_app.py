"""
Celery: beat + workers. See docker-compose (blue / green pools).

Host (backend venv):

  celery -A celery_app worker --loglevel=info
  celery -A celery_app beat --loglevel=info
"""

from __future__ import annotations

import logging
import os

from celery import Celery
from celery.signals import worker_init

from config import settings

logger = logging.getLogger(__name__)

app = Celery(
    "full_stack",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["celery_tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

app.conf.beat_schedule = {
    "drain-fastapi-redis-queue": {
        "task": "celery_tasks.drain_redis_queue",
        "schedule": settings.celery_beat_interval_seconds,
    },
}


@worker_init.connect
def _log_deployment_cohort(**_: object) -> None:
    cohort = os.environ.get("DEPLOYMENT_COHORT", "")
    release = os.environ.get("APP_RELEASE", "")
    parts = [f"cohort={cohort}"] if cohort else []
    if release:
        parts.append(f"release={release}")
    if parts:
        logger.info("Celery worker %s (blue/green ops)", " ".join(parts))
