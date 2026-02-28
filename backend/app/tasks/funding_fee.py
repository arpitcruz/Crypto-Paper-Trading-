"""Background task: apply funding fees to all open futures positions."""
import asyncio
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.models.position import Position, PositionStatus
from app.models.wallet import WalletType, TransactionType
import structlog

logger = structlog.get_logger()

FUNDING_RATE = 0.0001  # 0.01% per 8h = typical perpetual funding rate


@celery_app.task(name="app.tasks.funding_fee.apply_funding_fees")
def apply_funding_fees():
    asyncio.run(_apply_funding_fees())


async def _apply_funding_fees():
    from app.db.base import AsyncSessionLocal
    from app.services.market_data import fetch_current_price
    from app.services.wallet_service import record_transaction, get_wallet

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position).where(Position.status == PositionStatus.OPEN)
        )
        positions = result.scalars().all()

        for pos in positions:
            try:
                price = await fetch_current_price(pos.symbol)
                if not price:
                    continue

                position_value = pos.quantity * price
                funding_amount = position_value * FUNDING_RATE

                # Long pays short, short receives from long
                from app.models.order import PositionSide
                if pos.side == PositionSide.LONG:
                    funding_amount = -abs(funding_amount)
                else:
                    funding_amount = abs(funding_amount)

                pos.funding_fee += funding_amount
                wallet = await get_wallet(db, pos.user_id, WalletType.FUTURES)
                wallet.balance += funding_amount

                await record_transaction(
                    db, pos.user_id, wallet,
                    TransactionType.FUNDING_FEE,
                    funding_amount,
                    f"Funding fee: {pos.symbol} {pos.side.value}",
                    str(pos.id),
                )

                logger.debug("Funding fee applied", position_id=str(pos.id), amount=funding_amount)
            except Exception as e:
                logger.error("Error applying funding fee", error=str(e), position_id=str(pos.id))

        await db.commit()
