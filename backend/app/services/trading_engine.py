"""
Core trading engine handling order execution, position management,
liquidation logic, and PnL calculation for spot and futures markets.
"""
import asyncio
from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models.order import Order, OrderSide, OrderType, OrderStatus, MarketType, PositionSide, MarginMode
from app.models.position import Position, PositionStatus
from app.models.trade import Trade
from app.models.wallet import WalletType, TransactionType
from app.schemas.trading import PlaceOrderRequest
from app.services.market_data import fetch_current_price
from app.services.wallet_service import (
    get_wallet, debit_wallet, credit_wallet, lock_balance, unlock_balance, record_transaction
)
from app.core.config import settings
import structlog

logger = structlog.get_logger()

MAINTENANCE_MARGIN_RATE = 0.005  # 0.5%


async def place_order(db: AsyncSession, user_id: UUID, req: PlaceOrderRequest) -> Order:
    """Place a new order — validates balance, creates order, executes if market."""
    if req.symbol not in settings.SUPPORTED_PAIRS:
        raise HTTPException(status_code=400, detail=f"Unsupported trading pair: {req.symbol}")

    current_price = await fetch_current_price(req.symbol)
    if not current_price:
        raise HTTPException(status_code=503, detail="Unable to fetch current market price")

    execution_price = current_price
    if req.order_type == OrderType.LIMIT and req.price:
        execution_price = req.price

    wallet_type = WalletType.SPOT if req.market_type == MarketType.SPOT else WalletType.FUTURES
    fee_rate = settings.TRADING_FEE_SPOT if req.market_type == MarketType.SPOT else settings.TRADING_FEE_FUTURES

    if req.market_type == MarketType.FUTURES:
        leverage = min(req.leverage or 1, settings.MAX_LEVERAGE)
        margin_required = (execution_price * req.quantity) / leverage
    else:
        leverage = 1
        margin_required = execution_price * req.quantity if req.side == OrderSide.BUY else 0

    fee_amount = execution_price * req.quantity * fee_rate

    order = Order(
        user_id=user_id,
        symbol=req.symbol,
        market_type=req.market_type,
        order_type=req.order_type,
        side=req.side,
        status=OrderStatus.PENDING,
        price=req.price,
        stop_price=req.stop_price,
        quantity=req.quantity,
        filled_quantity=0.0,
        remaining_quantity=req.quantity,
        leverage=leverage,
        margin_mode=req.margin_mode or MarginMode.CROSS,
        position_side=req.position_side,
        take_profit=req.take_profit,
        stop_loss=req.stop_loss,
        fee_rate=fee_rate,
        fee_amount=0.0,
        margin_used=margin_required,
    )
    db.add(order)
    await db.flush()

    # For market orders, execute immediately
    if req.order_type == OrderType.MARKET:
        await _execute_order(db, order, user_id, current_price, wallet_type, fee_rate)
    elif req.order_type == OrderType.LIMIT:
        # Lock funds for limit orders
        total_locked = margin_required + fee_amount
        await lock_balance(db, user_id, wallet_type, total_locked)
        order.status = OrderStatus.OPEN

    return order


async def _execute_order(
    db: AsyncSession,
    order: Order,
    user_id: UUID,
    execution_price: float,
    wallet_type: WalletType,
    fee_rate: float,
):
    """Execute an order at the given price."""
    trade_value = execution_price * order.quantity
    fee_amount = trade_value * fee_rate

    if order.market_type == MarketType.SPOT:
        await _execute_spot_order(db, order, user_id, execution_price, trade_value, fee_amount, wallet_type)
    else:
        await _execute_futures_order(db, order, user_id, execution_price, trade_value, fee_amount)

    order.status = OrderStatus.FILLED
    order.avg_fill_price = execution_price
    order.filled_quantity = order.quantity
    order.remaining_quantity = 0.0
    order.fee_amount = fee_amount
    order.filled_at = datetime.utcnow()

    trade = Trade(
        user_id=user_id,
        order_id=order.id,
        symbol=order.symbol,
        market_type=order.market_type,
        side=order.side,
        price=execution_price,
        quantity=order.quantity,
        value=trade_value,
        fee=fee_amount,
        realized_pnl=0.0,
    )
    db.add(trade)


async def _execute_spot_order(
    db: AsyncSession,
    order: Order,
    user_id: UUID,
    execution_price: float,
    trade_value: float,
    fee_amount: float,
    wallet_type: WalletType,
):
    if order.side == OrderSide.BUY:
        total_cost = trade_value + fee_amount
        await debit_wallet(
            db, user_id, wallet_type, total_cost,
            TransactionType.TRADE_FEE,
            f"Buy {order.quantity} {order.symbol} @ {execution_price:.4f}",
            str(order.id),
        )
    else:
        proceeds = trade_value - fee_amount
        await credit_wallet(
            db, user_id, wallet_type, proceeds,
            TransactionType.REALIZED_PNL,
            f"Sell {order.quantity} {order.symbol} @ {execution_price:.4f}",
            str(order.id),
        )


async def _execute_futures_order(
    db: AsyncSession,
    order: Order,
    user_id: UUID,
    execution_price: float,
    trade_value: float,
    fee_amount: float,
):
    wallet_type = WalletType.FUTURES
    leverage = order.leverage
    margin_required = trade_value / leverage

    position_side = order.position_side
    if not position_side:
        position_side = PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT

    # Check if there's an existing position for this symbol/side
    result = await db.execute(
        select(Position).where(
            and_(
                Position.user_id == user_id,
                Position.symbol == order.symbol,
                Position.side == position_side,
                Position.status == PositionStatus.OPEN,
            )
        )
    )
    existing_position = result.scalar_one_or_none()

    is_opening = (
        (position_side == PositionSide.LONG and order.side == OrderSide.BUY) or
        (position_side == PositionSide.SHORT and order.side == OrderSide.SELL)
    )

    if is_opening:
        # Opening or increasing position
        total_cost = margin_required + fee_amount
        await debit_wallet(
            db, user_id, wallet_type, total_cost,
            TransactionType.TRADE_FEE,
            f"Open {position_side.value} {order.quantity} {order.symbol} @ {execution_price:.4f} x{leverage}",
            str(order.id),
        )

        if existing_position:
            # Average into existing position
            total_qty = existing_position.quantity + order.quantity
            avg_entry = (
                (existing_position.entry_price * existing_position.quantity) +
                (execution_price * order.quantity)
            ) / total_qty
            existing_position.quantity = total_qty
            existing_position.entry_price = avg_entry
            existing_position.initial_margin += margin_required
            existing_position.total_fee += fee_amount
            existing_position.liquidation_price = _calc_liquidation_price(
                avg_entry, position_side, leverage
            )
            existing_position.maintenance_margin = total_qty * execution_price * MAINTENANCE_MARGIN_RATE / leverage
        else:
            liq_price = _calc_liquidation_price(execution_price, position_side, leverage)
            position = Position(
                user_id=user_id,
                symbol=order.symbol,
                side=position_side,
                status=PositionStatus.OPEN,
                margin_mode=order.margin_mode,
                quantity=order.quantity,
                entry_price=execution_price,
                current_price=execution_price,
                leverage=leverage,
                initial_margin=margin_required,
                maintenance_margin=trade_value * MAINTENANCE_MARGIN_RATE / leverage,
                liquidation_price=liq_price,
                take_profit=order.take_profit,
                stop_loss=order.stop_loss,
                total_fee=fee_amount,
            )
            db.add(position)
    else:
        # Closing position
        if not existing_position:
            raise HTTPException(status_code=400, detail="No open position to close")

        close_qty = min(order.quantity, existing_position.quantity)
        realized_pnl = _calculate_realized_pnl(
            existing_position.entry_price, execution_price,
            position_side, close_qty, leverage
        )
        net_pnl = realized_pnl - fee_amount

        existing_position.realized_pnl += realized_pnl
        existing_position.total_fee += fee_amount

        await credit_wallet(
            db, user_id, wallet_type,
            margin_required + net_pnl,
            TransactionType.REALIZED_PNL,
            f"Close {position_side.value} {close_qty} {order.symbol} @ {execution_price:.4f} PnL: {net_pnl:.2f}",
            str(order.id),
        )

        if close_qty >= existing_position.quantity:
            existing_position.status = PositionStatus.CLOSED
            existing_position.closed_at = datetime.utcnow()
            existing_position.close_price = execution_price
            existing_position.close_reason = "manual"
        else:
            existing_position.quantity -= close_qty
            existing_position.initial_margin -= margin_required


def _calc_liquidation_price(entry_price: float, side: PositionSide, leverage: int) -> float:
    if side == PositionSide.LONG:
        return entry_price * (1 - (1 / leverage) + MAINTENANCE_MARGIN_RATE)
    else:
        return entry_price * (1 + (1 / leverage) - MAINTENANCE_MARGIN_RATE)


def _calculate_realized_pnl(
    entry_price: float,
    exit_price: float,
    side: PositionSide,
    quantity: float,
    leverage: int,
) -> float:
    if side == PositionSide.LONG:
        return (exit_price - entry_price) * quantity * leverage
    else:
        return (entry_price - exit_price) * quantity * leverage


async def update_positions_pnl(db: AsyncSession, user_id: UUID) -> list:
    """Update unrealized PnL for all open futures positions."""
    result = await db.execute(
        select(Position).where(
            and_(Position.user_id == user_id, Position.status == PositionStatus.OPEN)
        )
    )
    positions = result.scalars().all()
    updated = []

    for pos in positions:
        current_price = await fetch_current_price(pos.symbol)
        if current_price:
            pos.current_price = current_price
            pos.unrealized_pnl = _calculate_realized_pnl(
                pos.entry_price, current_price, pos.side, pos.quantity, pos.leverage
            )
            if pos.initial_margin > 0:
                pos.margin_ratio = abs(pos.unrealized_pnl) / pos.initial_margin
            updated.append(pos)

    await db.flush()
    return updated


async def check_and_liquidate_position(db: AsyncSession, position: Position, current_price: float) -> bool:
    """Check if a position should be liquidated and do it if so."""
    should_liquidate = False

    if position.side == PositionSide.LONG and current_price <= position.liquidation_price:
        should_liquidate = True
    elif position.side == PositionSide.SHORT and position.liquidation_price and current_price >= position.liquidation_price:
        should_liquidate = True

    # Check stop loss
    if position.stop_loss:
        if position.side == PositionSide.LONG and current_price <= position.stop_loss:
            should_liquidate = True
        elif position.side == PositionSide.SHORT and current_price >= position.stop_loss:
            should_liquidate = True

    # Check take profit
    if position.take_profit:
        if position.side == PositionSide.LONG and current_price >= position.take_profit:
            await _close_position_at_price(db, position, current_price, "tp")
            return False  # Not liquidated, just TP triggered

        elif position.side == PositionSide.SHORT and current_price <= position.take_profit:
            await _close_position_at_price(db, position, current_price, "tp")
            return False

    if should_liquidate:
        position.status = PositionStatus.LIQUIDATED
        position.closed_at = datetime.utcnow()
        position.close_price = current_price
        position.close_reason = "liquidation"
        position.realized_pnl = -position.initial_margin

        wallet = await get_wallet(db, position.user_id, WalletType.FUTURES)
        await record_transaction(
            db, position.user_id, wallet,
            TransactionType.LIQUIDATION,
            -position.initial_margin,
            f"Liquidation: {position.symbol} {position.side.value} @ {current_price:.4f}",
            str(position.id),
        )
        wallet.balance = max(0.0, wallet.balance - position.initial_margin)
        await db.flush()
        return True

    return False


async def _close_position_at_price(db: AsyncSession, position: Position, price: float, reason: str):
    realized_pnl = _calculate_realized_pnl(
        position.entry_price, price, position.side, position.quantity, position.leverage
    )
    fee = position.quantity * price * settings.TRADING_FEE_FUTURES
    net_pnl = realized_pnl - fee

    position.status = PositionStatus.CLOSED
    position.closed_at = datetime.utcnow()
    position.close_price = price
    position.close_reason = reason
    position.realized_pnl = realized_pnl

    wallet = await get_wallet(db, position.user_id, WalletType.FUTURES)
    refund = position.initial_margin + net_pnl
    wallet.balance += max(0.0, refund)
    await record_transaction(
        db, position.user_id, wallet,
        TransactionType.REALIZED_PNL,
        net_pnl,
        f"{reason.upper()}: {position.symbol} {position.side.value} PnL: {net_pnl:.2f}",
        str(position.id),
    )
    await db.flush()


async def cancel_order(db: AsyncSession, user_id: UUID, order_id: UUID) -> Order:
    result = await db.execute(
        select(Order).where(
            and_(Order.id == order_id, Order.user_id == user_id)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in [OrderStatus.OPEN, OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in status: {order.status}")

    order.status = OrderStatus.CANCELLED
    wallet_type = WalletType.SPOT if order.market_type == MarketType.SPOT else WalletType.FUTURES

    # Refund locked funds
    if order.margin_used > 0:
        await unlock_balance(db, user_id, wallet_type, order.margin_used)

    await db.flush()
    return order
