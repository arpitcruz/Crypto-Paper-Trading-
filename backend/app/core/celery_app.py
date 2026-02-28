from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "crypto_paper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.liquidation",
        "app.tasks.funding_fee",
        "app.tasks.price_alerts",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-liquidations": {
            "task": "app.tasks.liquidation.check_all_liquidations",
            "schedule": 5.0,  # every 5 seconds
        },
        "apply-funding-fees": {
            "task": "app.tasks.funding_fee.apply_funding_fees",
            "schedule": crontab(minute=0, hour="*/8"),  # every 8 hours
        },
        "check-price-alerts": {
            "task": "app.tasks.price_alerts.check_price_alerts",
            "schedule": 10.0,  # every 10 seconds
        },
        "cleanup-expired-orders": {
            "task": "app.tasks.liquidation.cleanup_expired_orders",
            "schedule": crontab(minute=0),  # every hour
        },
    }
)
