from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "opengrow",
    broker=settings.redis_broker_url,
    backend=settings.redis_result_url,
    include=["app.workers.tasks"],
)

celery.conf.update(
    task_default_queue="cpu_light",
    task_queues={
        "cpu_light": {"exchange": "cpu_light", "routing_key": "cpu_light"},
        "gen_heavy": {"exchange": "gen_heavy", "routing_key": "gen_heavy"},
    },
    task_routes={
        "app.workers.tasks.scan_asset": {"queue": "cpu_light"},
        "app.workers.tasks.embed_asset": {"queue": "cpu_light"},
        "app.workers.tasks.notify_email": {"queue": "cpu_light"},
        "app.workers.tasks.run_generation": {"queue": "gen_heavy"},
        "app.workers.tasks.run_orchestrator": {"queue": "gen_heavy"},
        "app.workers.tasks.sync_analytics_connector": {"queue": "cpu_light"},
        "app.workers.tasks.sync_connected_analytics_connectors": {"queue": "cpu_light"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=60 * 60 * 24,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "clamav-refresh-daily": {
            "task": "app.workers.tasks.refresh_clamav_signatures",
            "schedule": crontab(hour=3, minute=0),
        },
        "analytics-connectors-sync-daily": {
            "task": "app.workers.tasks.sync_connected_analytics_connectors",
            "schedule": crontab(hour=4, minute=0),
        },
    },
)
