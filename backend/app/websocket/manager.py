"""
WebSocket connection manager — handles client connections for:
- Real-time price streaming from Binance
- Position PnL updates
- Order/trade notifications
"""
import asyncio
import json
import websockets
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.core.config import settings
from app.db.redis import cache_price
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        # symbol -> set of WebSocket clients
        self.price_subscribers: Dict[str, Set[WebSocket]] = {}
        # user_id -> WebSocket
        self.user_connections: Dict[str, WebSocket] = {}
        self._binance_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._binance_task: Optional[asyncio.Task] = None

    async def connect_user(self, ws: WebSocket, user_id: str):
        await ws.accept()
        self.user_connections[user_id] = ws
        logger.info("User connected via WebSocket", user_id=user_id)

    def disconnect_user(self, user_id: str):
        self.user_connections.pop(user_id, None)
        logger.info("User disconnected from WebSocket", user_id=user_id)

    async def subscribe_to_symbol(self, ws: WebSocket, symbol: str):
        if symbol not in self.price_subscribers:
            self.price_subscribers[symbol] = set()
        self.price_subscribers[symbol].add(ws)

    async def unsubscribe_from_symbol(self, ws: WebSocket, symbol: str):
        if symbol in self.price_subscribers:
            self.price_subscribers[symbol].discard(ws)

    async def broadcast_price(self, symbol: str, data: dict):
        if symbol not in self.price_subscribers:
            return
        dead = set()
        for ws in self.price_subscribers[symbol].copy():
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.price_subscribers[symbol].discard(ws)

    async def send_to_user(self, user_id: str, data: dict):
        ws = self.user_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.user_connections.pop(user_id, None)

    async def start_binance_stream(self):
        """Start streaming live prices from Binance WebSocket."""
        streams = "/".join([f"{pair.lower()}@ticker" for pair in settings.SUPPORTED_PAIRS])
        url = f"{settings.BINANCE_WS_URL}/stream?streams={streams}"

        while True:
            try:
                logger.info("Connecting to Binance WebSocket", url=url)
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self._binance_ws = ws
                    async for message in ws:
                        await self._handle_binance_message(message)
            except Exception as e:
                logger.error("Binance WebSocket error, reconnecting in 5s", error=str(e))
                await asyncio.sleep(5)

    async def _handle_binance_message(self, raw_message: str):
        try:
            wrapper = json.loads(raw_message)
            data = wrapper.get("data", wrapper)

            symbol = data.get("s")
            if not symbol or symbol not in settings.SUPPORTED_PAIRS:
                return

            price = float(data.get("c", 0))
            if price <= 0:
                return

            # Cache to Redis
            await cache_price(symbol, price)

            # Broadcast to subscribers
            ticker_data = {
                "type": "ticker",
                "symbol": symbol,
                "price": price,
                "change_24h": float(data.get("P", 0)),
                "high_24h": float(data.get("h", 0)),
                "low_24h": float(data.get("l", 0)),
                "volume_24h": float(data.get("v", 0)),
            }
            await self.broadcast_price(symbol, ticker_data)

        except Exception as e:
            logger.error("Error handling Binance message", error=str(e))

    def start_background_stream(self):
        """Launch Binance stream as a background task."""
        self._binance_task = asyncio.create_task(self.start_binance_stream())
        return self._binance_task


manager = ConnectionManager()
