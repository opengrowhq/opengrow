from app.celery_app import celery


def test_connector_sync_is_scheduled_daily():
    schedule = celery.conf.beat_schedule["analytics-connectors-sync-daily"]

    assert schedule["task"] == "app.workers.tasks.sync_connected_analytics_connectors"


def test_connector_sync_tasks_route_to_light_queue():
    routes = celery.conf.task_routes

    assert routes["app.workers.tasks.sync_analytics_connector"]["queue"] == "cpu_light"
    assert (
        routes["app.workers.tasks.sync_connected_analytics_connectors"]["queue"]
        == "cpu_light"
    )
