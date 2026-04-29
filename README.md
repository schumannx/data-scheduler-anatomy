# full-stack-data-app — schedules

## How it works (data flow)

```text
Browser form
  → FastAPI saves a row in MongoDB (“schedule”)
       ↓
FastAPI scheduler (every ~30s)
  → For each row that is “active” (between start/end dates)
    and “due” (next_run ≤ now)
  → Pushes one JSON blob onto a Redis list (full_stack:due_jobs)
    and updates next_run in Mongo (next cron time)
       ↓
Celery beat (every ~10s)
  → Tells workers to run drain_redis_queue
       ↓
Celery worker(s)
  → LPOP from that same Redis list
  → For each message, runs process_schedule_job (prints/logs the name)
```

MongoDB holds **schedule definitions**; the Redis list is a short **queue of fired jobs**; Celery **consumes** that queue. Intervals come from `SCHEDULER_INTERVAL_SECONDS` and `CELERY_BEAT_INTERVAL_SECONDS` in `.env` / `backend/.env` (see `.env.example`).

---

## Run MongoDB + Redis

From this folder:

```bash
docker compose up -d
```

Starts **MongoDB** and **Redis**. API and UI usually run on your machine.

### Celery in Docker (optional)

- **`celery`** profile — beat + **green** workers (day-to-day pool).
- **`celery-blue`** profile — optional **blue** pool during a deploy cutover.

```bash
docker compose --profile celery up -d
docker compose --profile celery --profile celery-blue up -d   # optional second pool
```

Retire blue after tasks drain (graceful stop):

```bash
docker compose stop -t 120 celery-worker-blue
```

**Blue / green:** Two worker pools, **same** Redis and **same** tasks. Steady state = green only. Briefly run blue + green when switching releases; then stop blue. Only **one** `celery-beat`. Image tags / `APP_RELEASE_*` in `.env` next to `docker-compose.yml` — see `.env.example`.

**Host-only Celery** (no Docker): from `backend/` — `celery -A celery_app worker` and `celery -A celery_app beat`. Containers use `redis://redis:6379`; local Uvicorn uses `localhost` in `backend/.env`.

### Tests (Celery drain)

```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```

Mocks Redis; uses Celery eager mode (no broker).

### Watch the pipeline

1. **Uvicorn** — `Enqueued N due schedule(s) to Redis`
2. **Worker** — `[Celery] process_schedule_job name='…'`
3. **Redis** — `docker compose exec redis redis-cli LLEN full_stack:due_jobs`
4. **Beat** — `docker compose logs -f celery-beat`

---

## Run API

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Run React UI

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and submit the form.

Health check: **http://127.0.0.1:8000/api/health** · Redis list: `redis-cli LRANGE full_stack:due_jobs 0 -1`
