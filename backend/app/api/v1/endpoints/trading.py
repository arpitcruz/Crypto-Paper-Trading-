from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from uuid import UUID
from typing import List, Optional

from app.db.base import get_db
from app.models.user import User
from app.models.order import Order, OrderStatus, MarketType
from app.models.position import Position, PositionStatus
from app.models.trade import Trade
from app.models.wallet import Wallet, Transaction
from app.schemas.trading import (
    PlaceOrderRequest, OrderResponse, PositionResponse, TradeResponse,
    WalletResponse, TransferRequest, ClosePositionRequest, UpdatePositionRiskRequest
)
from app.services.trading_engine import (
    place_order, cancel_order, update_positions_pnl, check_and_liquidate_position
)
from app.services.wallet_service import (
    get_or_create_wallets, reset_wallet, transfer_between_wallets
)
from app.services.market_data import fetch_current_price
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/trading", tags=["Trading"])


@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    payload: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await place_order(db, current_user.id, payload)
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    market_type: Optional[MarketType] = None,
    status: Optional[OrderStatus] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).where(Order.user_id == current_user.id)
    if market_type:
        query = query.where(Order.market_type == market_type)
    if status:
        query = query.where(Order.status == status)
    if symbol:
        query = query.where(Order.symbol == symbol)
    query = query.order_by(desc(Order.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/orders/{order_id}", response_model=OrderResponse)
async def cancel_existing_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await cancel_order(db, current_user.id, order_id)
    await db.commit()
    return order


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    status: Optional[PositionStatus] = PositionStatus.OPEN,
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Position).where(Position.user_id == current_user.id)
    if status:
        query = query.where(Position.status == status)
    if symbol:
        query = query.where(Position.symbol == symbol)
    query = query.order_by(desc(Position.opened_at))
    result = await db.execute(query)
    positions = result.scalars().all()

    # Update PnL with live prices
    for pos in positions:
        if pos.status == PositionStatus.OPEN:
            current_price = await fetch_current_price(pos.symbol)
            if current_price:
                pos.current_price = current_price
                from app.models.order import PositionSide
                from app.services.trading_engine import _calculate_realized_pnl
                pos.unrealized_pnl = _calculate_realized_pnl(
                    pos.entry_price, current_price, pos.side, pos.quantity, pos.leverage
                )
                if pos.initial_margin > 0:
                    pos.roe_percent = (pos.unrealized_pnl / pos.initial_margin) * 100

    return positions


@router.post("/positions/close")
async def close_position(
    payload: ClosePositionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Position).where(
            and_(
                Position.id == payload.position_id,
                Position.user_id == current_user.id,
                Position.status == PositionStatus.OPEN,
            )
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=404, detail="Open position not found")

    current_price = await fetch_current_price(position.symbol)
    if not current_price:
        raise HTTPException(status_code=503, detail="Unable to fetch current price")

    from app.models.order import OrderSide, OrderType
    close_side = OrderSide.SELL if position.side.value == "long" else OrderSide.BUY
    close_qty = payload.quantity or position.quantity

    close_req = PlaceOrderRequest(
        symbol=position.symbol,
        market_type=MarketType.FUTURES,
        order_type=OrderType.MARKET,
        side=close_side,
        quantity=close_qty,
        position_side=position.side,
    )
    order = await place_order(db, current_user.id, close_req)
    await db.commit()
    return {"message": "Position closed", "order_id": str(order.id)}


@router.put("/positions/risk")
async def update_position_risk(
    payload: UpdatePositionRiskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Position).where(
            and_(
                Position.id == payload.position_id,
                Position.user_id == current_user.id,
                Position.status == PositionStatus.OPEN,
            )
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=404, detail="Open position not found")

    if payload.take_profit is not None:
        position.take_profit = payload.take_profit
    if payload.stop_loss is not None:
        position.stop_loss = payload.stop_loss

    await db.commit()
    return {"message": "Risk parameters updated"}


@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    symbol: Optional[str] = None,
    market_type: Optional[MarketType] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Trade).where(Trade.user_id == current_user.id)
    if symbol:
        query = query.where(Trade.symbol == symbol)
    if market_type:
        query = query.where(Trade.market_type == market_type)
    query = query.order_by(desc(Trade.executed_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/wallet", response_model=List[WalletResponse])
async def get_wallets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wallets = await get_or_create_wallets(db, current_user.id)
    await db.commit()
    return list(wallets.values())


@router.post("/wallet/transfer")
async def transfer_funds(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await transfer_between_wallets(
        db, current_user.id, payload.from_wallet, payload.to_wallet, payload.amount
    )
    await db.commit()
    return {"message": f"Transferred ${payload.amount:.2f} successfully"}


@router.post("/wallet/reset")
async def reset_user_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await reset_wallet(db, current_user.id)
    await db.commit()
    return {"message": "Wallet reset to default balance"}


@router.get("/transactions")
async def get_transactions(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(desc(Transaction.created_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/stats")
async def get_trading_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.order import OrderSide
    trades_result = await db.execute(select(Trade).where(Trade.user_id == current_user.id))
    trades = trades_result.scalars().all()

    total_trades = len(trades)
    total_pnl = sum(t.realized_pnl for t in trades)
    winning = [t for t in trades if t.realized_pnl > 0]
    losing = [t for t in trades if t.realized_pnl < 0]

    return {
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": (len(winning) / total_trades * 100) if total_trades > 0 else 0,
        "total_pnl": total_pnl,
        "total_volume": sum(t.value for t in trades),
        "best_trade": max((t.realized_pnl for t in trades), default=0),
        "worst_trade": min((t.realized_pnl for t in trades), default=0),
        "avg_pnl": total_pnl / total_trades if total_trades > 0 else 0,
    }
