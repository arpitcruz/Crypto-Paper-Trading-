"""Background task: check and execute liquidations for all open positions."""
import asyncio
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.models.position import Position, PositionStatus
from app.models.order import Order, OrderStatus
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


@celery_app.task(name="app.tasks.liquidation.check_all_liquidations")
def check_all_liquidations():
    asyncio.run(_check_all_liquidations())


async def _check_all_liquidations():
    from app.db.base import AsyncSessionLocal
    from app.services.market_data import fetch_current_price
    from app.services.trading_engine import check_and_liquidate_position

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position).where(Position.status == PositionStatus.OPEN)
        )
        positions = result.scalars().all()

        for position in positions:
            try:
                price = await fetch_current_price(position.symbol)
                if price:
                    liquidated = await check_and_liquidate_position(db, position, price)
                    if liquidated:
                        logger.info(
                            "Position liquidated",
                            position_id=str(position.id),
                            symbol=position.symbol,
                            price=price,
                        )
            except Exception as e:
                logger.error("Error checking liquidation", error=str(e), position_id=str(position.id))

        await db.commit()


@celery_app.task(name="app.tasks.liquidation.cleanup_expired_orders")
def cleanup_expired_orders():
    asyncio.run(_cleanup_expired_orders())


async def _cleanup_expired_orders():
    from app.db.base import AsyncSessionLocal

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Order).where(
                Order.status.in_([OrderStatus.OPEN, OrderStatus.PENDING]),
                Order.expires_at != None,
                Order.expires_at < now,
            )
        )
        orders = result.scalars().all()
        for order in orders:
            order.status = OrderStatus.EXPIRED
            logger.info("Order expired", order_id=str(order.id))

        await db.commit()
