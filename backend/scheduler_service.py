"""Periodic tick: find due schedules in MongoDB and push payloads to Redis (bounded async pool)."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from bson import ObjectId
from croniter import croniter
from redis.asyncio import Redis

from config import settings
from db import schedules_collection

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _next_cron_after(cron_expr: str, after: datetime) -> datetime:
    itr = croniter(cron_expr, after)
    nxt = itr.get_next(datetime)
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=timezone.utc)
    return nxt


async def _push_one(redis: Redis, doc: dict) -> None:
    payload = {
        "schedule_id": str(doc["_id"]),
        "name": doc["name"],
        "cron": doc["cron"],
        "fired_at": _utc_now().isoformat(),
    }
    await redis.rpush(settings.redis_queue_key, json.dumps(payload, default=str))


async def process_due_schedules(redis: Redis) -> int:
    """Return number of jobs enqueued."""
    now = _utc_now()
    coll = schedules_collection()
    query = {
        "start_date": {"$lte": now},
        "end_date": {"$gte": now},
        "next_run": {"$lte": now},
    }
    cursor = coll.find(query)
    docs = await cursor.to_list(length=500)
    if not docs:
        return 0

    sem = asyncio.Semaphore(settings.worker_pool_size)

    async def bounded_push(doc: dict) -> None:
        async with sem:
            await _push_one(redis, doc)
            new_next = _next_cron_after(doc["cron"], now)
            await coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"next_run": new_next, "last_enqueued_at": now}},
            )

    await asyncio.gather(*(bounded_push(d) for d in docs))
    logger.info("Enqueued %s due schedule(s) to Redis", len(docs))
    return len(docs)


async def scheduler_loop(redis: Redis, stop: asyncio.Event) -> None:
    interval = settings.scheduler_interval_seconds
    while True:
        try:
            await process_due_schedules(redis)
        except Exception:
            logger.exception("Scheduler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except asyncio.TimeoutError:
            pass
