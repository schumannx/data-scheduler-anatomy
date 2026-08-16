import asyncio
import logging
from contextlib import asynccontextmanager

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from config import settings
from db import schedules_collection
from schemas import ScheduleCreate, ScheduleOut
from scheduler_service import scheduler_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client: Redis | None = None
_scheduler_task: asyncio.Task | None = None
_stop_scheduler = asyncio.Event()


def _doc_to_out(doc: dict) -> ScheduleOut:
    return ScheduleOut(
        id=str(doc["_id"]),
        name=doc["name"],
        cron=doc["cron"],
        next_run=doc["next_run"],
        start_date=doc["start_date"],
        end_date=doc["end_date"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, _scheduler_task
    coll = schedules_collection()
    await coll.create_index([("next_run", 1), ("start_date", 1), ("end_date", 1)])

    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    _stop_scheduler.clear()
    _scheduler_task = asyncio.create_task(scheduler_loop(redis_client, _stop_scheduler))

    yield

    _stop_scheduler.set()
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    if redis_client:
        await redis_client.aclose()
    redis_client = None


app = FastAPI(title="Data Scheduler Anatomy", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/schedules", response_model=ScheduleOut)
async def create_schedule(body: ScheduleCreate):
    doc = body.model_dump()
    result = await schedules_collection().insert_one(doc)
    created = await schedules_collection().find_one({"_id": result.inserted_id})
    if not created:
        raise HTTPException(500, "Insert failed")
    return _doc_to_out(created)


@app.get("/api/schedules", response_model=list[ScheduleOut])
async def list_schedules():
    cursor = schedules_collection().find().sort("next_run", 1).limit(200)
    docs = await cursor.to_list(length=200)
    return [_doc_to_out(d) for d in docs]


@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    try:
        oid = ObjectId(schedule_id)
    except Exception:
        raise HTTPException(400, "Invalid id") from None
    res = await schedules_collection().delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"deleted": True}
