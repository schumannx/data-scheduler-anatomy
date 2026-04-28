import pytest

import celery_app


@pytest.fixture(autouse=True)
def celery_eager_mode():
    """Run .delay() synchronously in tests (no broker)."""
    prev_always = celery_app.app.conf.task_always_eager
    prev_propagate = celery_app.app.conf.task_eager_propagates
    celery_app.app.conf.task_always_eager = True
    celery_app.app.conf.task_eager_propagates = True
    yield
    celery_app.app.conf.task_always_eager = prev_always
    celery_app.app.conf.task_eager_propagates = prev_propagate
