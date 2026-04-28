# full-stack-data-app — schedules

Project folder: **full-stack-data-app** (can live anywhere you keep it).

## Open in Cursor

**File → Open Folder…** → choose:

`/path/to/full-stack-data-app`

## Run MongoDB + Redis

From this folder:

```bash
docker compose up -d
```

That starts **MongoDB** and **Redis** only (API and UI still run on your machine by default).

### Celery in Docker (optional)

Use profile **`celery`** for **beat + green workers** (the “current” pool). Use **`celery-blue`** only while simulating a cutover (old + new pools at once).

```bash
docker compose --profile celery up -d
# Optional second pool (blue = “previous” release):
docker compose --profile celery --profile celery-blue up -d
```

Stop old pool after tasks drain (graceful, no hard kill mid-task):

```bash
docker compose stop -t 120 celery-worker-blue
```

**Blue / green (two sides, not three stacks):** At steady state you run **one** worker cohort (e.g. **green**). During a release you may run **blue + green** briefly; **release 01 → 02 → 03** is **versioning over time**, not “three Celery stacks forever.” **One** `celery-beat` — do not run duplicate beats with the same schedule.

**Versioned images:** Green and blue build as **different image tags** (`full-stack-data-celery:green`, `:blue`, `:beat` by default). Set **`APP_RELEASE_GREEN`** / **`APP_RELEASE_BLUE`** in a **`.env` file next to `docker-compose.yml`** (Compose loads it) to stamp the image label and task logs. Optional: **`CELERY_GREEN_TAG`**, **`CELERY_BLUE_TAG`**, **`CELERY_BEAT_TAG`** to pin tag names (see `.env.example`).

Host-only Celery (no Docker): from `backend/` with venv — `celery -A celery_app worker` and `celery -A celery_app beat`. Containers use `redis://redis:6379` and `mongodb://mongodb:27017`; your local `backend/.env` keeps `localhost` for Uvicorn.

### What blue and green are doing

In **this repo**, blue and green are **not** separate Redis servers and **not** separate application code paths. They are **two optional Celery worker pools** in Docker:

| Pool | Typical meaning |
|------|------------------|
| **Green** (`celery-worker-green`) | The **current** release you run day to day (`--profile celery`). |
| **Blue** (`celery-worker-blue`) | The **previous** release you only bring up **during a deploy** (`--profile celery-blue` alongside green). |

**Both** connect to the **same** Redis and run the **same** tasks (`drain_redis_queue`, `process_schedule_job`). Any idle worker can pick up broker messages. The labels (`DEPLOYMENT_COHORT`, `APP_RELEASE`, image tags) are for **operations**: you can run green on image `release-03`, briefly keep blue on `release-02`, then **stop blue** after work drains (`docker compose stop -t 120 celery-worker-blue`). **One** `celery-beat` — never run two beats with the same schedule without extra coordination.

### Automated tests (Celery drain logic)

From `backend/` with venv:

```bash
python -m pytest tests/ -v
```

These tests **mock Redis** and use Celery **eager mode** (tasks run in-process). They check: empty queue, one job, bad JSON skipped, non-object JSON skipped, multiple jobs in one drain.

### Watch the pipeline (manual)

1. **FastAPI** terminal — look for `Enqueued N due schedule(s) to Redis` (scheduler → Redis list).  
2. **Celery worker** logs — `docker compose logs -f celery-worker-green` or host worker terminal; look for `[Celery] process_schedule_job name='…'`.  
3. **Redis** — `docker compose exec redis redis-cli LLEN full_stack:due_jobs` (often `0` if Celery is draining quickly).  
4. **Beat** — `docker compose logs -f celery-beat` (confirms periodic `drain_redis_queue` is being scheduled).

## Run API

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --reload --port 8000
```

## Run React UI

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, submit the form. Jobs are stored in MongoDB; every ~30s the API enqueues due rows (within start/end and `next_run` passed) to the Redis list `full_stack:due_jobs` (see `.env.example`).

Inspect Redis: `redis-cli LRANGE full_stack:due_jobs 0 -1`
