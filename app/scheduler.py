from __future__ import annotations

import threading

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

_scheduler: BackgroundScheduler | None = None
_running_jobs_lock = threading.Lock()
_running_job_ids: set[str] = set()


def get_running_job_ids() -> frozenset[str]:
    with _running_jobs_lock:
        return frozenset(_running_job_ids)


def init_scheduler(app: Flask) -> None:
    global _scheduler
    if _scheduler is not None:
        return

    scheduler = BackgroundScheduler(daemon=True)
    job_id = "fetch_weather"

    def fetch_job() -> None:
        with _running_jobs_lock:
            _running_job_ids.add(job_id)
        try:
            with app.app_context():
                from app.services.weather import fetch_due_cities

                fetch_due_cities()
        finally:
            with _running_jobs_lock:
                _running_job_ids.discard(job_id)

    scheduler.add_job(fetch_job, "interval", minutes=1, id=job_id)
    scheduler.start()
    _scheduler = scheduler

    @app.teardown_appcontext
    def shutdown_scheduler(exception: BaseException | None = None) -> None:
        pass


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler
