from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "ai-super-assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["workflow.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    beat_schedule={
        "check-workflows-every-minute": {
            "task": "workflow.tasks.check_scheduled_workflows",
            "schedule": 60.0,
        },
    },
)
