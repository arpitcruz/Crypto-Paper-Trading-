"""Background task: check and trigger price alerts."""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, and_
from app.core.celery_app import celery_app
from app.models.alert import PriceAlert, AlertCondition
from app.websocket.manager import manager
import structlog

logger = structlog.get_logger()


@celery_app.task(name="app.tasks.price_alerts.check_price_alerts")
def check_price_alerts():
    asyncio.run(_check_price_alerts())


async def _check_price_alerts():
    from app.db.base import AsyncSessionLocal
    from app.services.market_data import fetch_current_price

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PriceAlert).where(
                and_(PriceAlert.is_active == True, PriceAlert.is_triggered == False)
            )
        )
        alerts = result.scalars().all()

        for alert in alerts:
            try:
                price = await fetch_current_price(alert.symbol)
                if not price:
                    continue

                triggered = False
                if alert.condition == AlertCondition.ABOVE and price >= alert.target_price:
                    triggered = True
                elif alert.condition == AlertCondition.BELOW and price <= alert.target_price:
                    triggered = True

                if triggered:
                    alert.is_triggered = True
                    alert.triggered_at = datetime.now(timezone.utc)

                    # Notify user via WebSocket
                    await manager.send_to_user(str(alert.user_id), {
                        "type": "price_alert",
                        "symbol": alert.symbol,
                        "target_price": alert.target_price,
                        "current_price": price,
                        "condition": alert.condition.value,
                    })
                    logger.info(
                        "Price alert triggered",
                        user_id=str(alert.user_id),
                        symbol=alert.symbol,
                        price=price,
                    )
            except Exception as e:
                logger.error("Error checking price alert", error=str(e), alert_id=str(alert.id))

        await db.commit()
