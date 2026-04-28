"""Tests for Celery drain → process_schedule_job (Redis list is mocked)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import celery_tasks
from celery_tasks import drain_redis_queue


@pytest.fixture
def mock_redis(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(celery_tasks, "_redis_sync", lambda: client)
    return client


def test_drain_empty_queue(mock_redis):
    mock_redis.lpop.return_value = None
    out = drain_redis_queue()
    assert out == {"dispatched": 0, "queue_key": celery_tasks.settings.redis_queue_key}
    mock_redis.lpop.assert_called_once()


def test_drain_one_valid_job(mock_redis):
    payload = {
        "schedule_id": "abc123",
        "name": "unit-test-job",
        "cron": "*/5 * * * *",
        "fired_at": "2026-01-01T12:00:00+00:00",
    }
    mock_redis.lpop.side_effect = [json.dumps(payload), None]
    out = drain_redis_queue()
    assert out["dispatched"] == 1
    assert out["queue_key"] == celery_tasks.settings.redis_queue_key


def test_drain_skips_bad_json(mock_redis):
    mock_redis.lpop.side_effect = ["not-json", None]
    out = drain_redis_queue()
    assert out["dispatched"] == 0


def test_drain_skips_non_object_json(mock_redis):
    mock_redis.lpop.side_effect = [json.dumps(["a", "list"]), None]
    out = drain_redis_queue()
    assert out["dispatched"] == 0


def test_drain_multiple_in_one_tick(mock_redis):
    p1 = {"schedule_id": "1", "name": "a", "cron": "* * * * *", "fired_at": "2026-01-01T00:00:00+00:00"}
    p2 = {"schedule_id": "2", "name": "b", "cron": "* * * * *", "fired_at": "2026-01-01T00:00:00+00:00"}
    mock_redis.lpop.side_effect = [json.dumps(p1), json.dumps(p2), None]
    out = drain_redis_queue()
    assert out["dispatched"] == 2
