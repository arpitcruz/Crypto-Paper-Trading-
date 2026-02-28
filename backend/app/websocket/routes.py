import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select, and_
from app.core.security import verify_token
from app.db.base import AsyncSessionLocal
from app.models.user import User
from app.models.position import Position, PositionStatus
from app.services.market_data import fetch_current_price
from app.services.trading_engine import _calculate_realized_pnl
from app.websocket.manager import manager
import asyncio

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/market/{symbol}")
async def market_websocket(websocket: WebSocket, symbol: str):
    """Stream live price data for a specific symbol."""
    symbol = symbol.upper()
    await websocket.accept()
    await manager.subscribe_to_symbol(websocket, symbol)

    try:
        while True:
            # Keep connection alive, wait for client messages
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        await manager.unsubscribe_from_symbol(websocket, symbol)


@router.websocket("/ws/market")
async def all_market_websocket(websocket: WebSocket):
    """Stream live price data for all supported pairs."""
    from app.core.config import settings
    await websocket.accept()

    for symbol in settings.SUPPORTED_PAIRS:
        await manager.subscribe_to_symbol(websocket, symbol)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("action") == "subscribe" and data.get("symbol"):
                    await manager.subscribe_to_symbol(websocket, data["symbol"].upper())
                elif data.get("action") == "unsubscribe" and data.get("symbol"):
                    await manager.unsubscribe_from_symbol(websocket, data["symbol"].upper())
                elif data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        from app.core.config import settings
        for symbol in settings.SUPPORTED_PAIRS:
            await manager.unsubscribe_from_symbol(websocket, symbol)


@router.websocket("/ws/user")
async def user_websocket(websocket: WebSocket, token: str = Query(...)):
    """Authenticated WebSocket for user-specific updates (positions, orders, PnL)."""
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = payload["sub"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.is_blocked:
            await websocket.close(code=4003, reason="Forbidden")
            return

    await manager.connect_user(websocket, user_id)

    try:
        # Start sending live PnL updates every 3 seconds
        async def send_pnl_updates():
            while True:
                try:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(Position).where(
                                and_(
                                    Position.user_id == user_id,
                                    Position.status == PositionStatus.OPEN,
                                )
                            )
                        )
                        positions = result.scalars().all()
                        updates = []
                        for pos in positions:
                            price = await fetch_current_price(pos.symbol)
                            if price:
                                pnl = _calculate_realized_pnl(
                                    pos.entry_price, price, pos.side, pos.quantity, pos.leverage
                                )
                                roe = (pnl / pos.initial_margin * 100) if pos.initial_margin > 0 else 0
                                updates.append({
                                    "position_id": str(pos.id),
                                    "symbol": pos.symbol,
                                    "unrealized_pnl": round(pnl, 4),
                                    "roe_percent": round(roe, 2),
                                    "current_price": price,
                                })

                        if updates:
                            await manager.send_to_user(user_id, {
                                "type": "pnl_update",
                                "positions": updates,
                            })
                except Exception as e:
                    pass
                await asyncio.sleep(3)

        pnl_task = asyncio.create_task(send_pnl_updates())

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        pnl_task.cancel()
        manager.disconnect_user(user_id)
