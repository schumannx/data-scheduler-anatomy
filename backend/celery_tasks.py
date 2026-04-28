"""
Drain FastAPI's Redis list into Celery tasks; each task prints the schedule name.
"""

from __future__ import annotations

import json
import logging

import redis
from celery_app import app

from config import settings

logger = logging.getLogger(__name__)


def _redis_sync() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@app.task(name="celery_tasks.process_schedule_job")
def process_schedule_job(payload: dict) -> str:
    name = payload.get("name") or ""
    line = f"[Celery] process_schedule_job name={name!r} schedule_id={payload.get('schedule_id')!r}"
    print(line, flush=True)
    logger.info("process_schedule_job name=%s schedule_id=%s", name, payload.get("schedule_id"))
    return name


@app.task(name="celery_tasks.drain_redis_queue")
def drain_redis_queue() -> dict:
    client = _redis_sync()
    key = settings.redis_queue_key
    dispatched = 0
    while True:
        raw = client.lpop(key)
        if raw is None:
            break
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSON from Redis: %s", raw[:200])
            continue
        if not isinstance(payload, dict):
            logger.warning("Skipping non-object payload: %s", type(payload).__name__)
            continue
        process_schedule_job.delay(payload)
        dispatched += 1
    if dispatched:
        logger.info("Drained %s job(s) from %s", dispatched, key)
    return {"dispatched": dispatched, "queue_key": key}
