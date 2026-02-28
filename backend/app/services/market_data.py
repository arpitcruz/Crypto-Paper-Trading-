import asyncio
import json
import aiohttp
from typing import Optional, Dict, List
from app.core.config import settings
from app.db.redis import cache_price, get_cached_price, cache_orderbook, get_cached_orderbook
import structlog

logger = structlog.get_logger()

_price_cache: Dict[str, float] = {}


async def fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch current price from cache or Binance API."""
    cached = await get_cached_price(symbol)
    if cached:
        return cached

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{settings.BINANCE_REST_URL}/api/v3/ticker/price"
            async with session.get(url, params={"symbol": symbol}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = float(data["price"])
                    await cache_price(symbol, price)
                    _price_cache[symbol] = price
                    return price
    except Exception as e:
        logger.error("Failed to fetch price", symbol=symbol, error=str(e))
        return _price_cache.get(symbol)


async def fetch_ticker_24h(symbol: str) -> Optional[dict]:
    """Fetch 24h ticker stats from Binance."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{settings.BINANCE_REST_URL}/api/v3/ticker/24hr"
            async with session.get(url, params={"symbol": symbol}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "symbol": data["symbol"],
                        "price": float(data["lastPrice"]),
                        "change_24h": float(data["priceChange"]),
                        "change_percent_24h": float(data["priceChangePercent"]),
                        "high_24h": float(data["highPrice"]),
                        "low_24h": float(data["lowPrice"]),
                        "volume_24h": float(data["volume"]),
                        "quote_volume_24h": float(data["quoteVolume"]),
                    }
    except Exception as e:
        logger.error("Failed to fetch 24h ticker", symbol=symbol, error=str(e))
    return None


async def fetch_all_tickers() -> List[dict]:
    """Fetch tickers for all supported pairs."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{settings.BINANCE_REST_URL}/api/v3/ticker/24hr"
            symbols = json.dumps(settings.SUPPORTED_PAIRS)
            async with session.get(url, params={"symbols": symbols}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = []
                    for item in data:
                        result.append({
                            "symbol": item["symbol"],
                            "price": float(item["lastPrice"]),
                            "change_24h": float(item["priceChange"]),
                            "change_percent_24h": float(item["priceChangePercent"]),
                            "high_24h": float(item["highPrice"]),
                            "low_24h": float(item["lowPrice"]),
                            "volume_24h": float(item["volume"]),
                        })
                    return result
    except Exception as e:
        logger.error("Failed to fetch all tickers", error=str(e))
    return []


async def fetch_klines(symbol: str, interval: str = "1h", limit: int = 200) -> List[dict]:
    """Fetch candlestick data from Binance."""
    valid_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w"]
    if interval not in valid_intervals:
        interval = "1h"

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{settings.BINANCE_REST_URL}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    raw = await resp.json()
                    return [
                        {
                            "time": k[0],
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5]),
                            "close_time": k[6],
                        }
                        for k in raw
                    ]
    except Exception as e:
        logger.error("Failed to fetch klines", symbol=symbol, interval=interval, error=str(e))
    return []


async def fetch_orderbook(symbol: str, limit: int = 20) -> Optional[dict]:
    """Fetch order book depth from Binance."""
    cached = await get_cached_orderbook(symbol)
    if cached:
        return cached

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{settings.BINANCE_REST_URL}/api/v3/depth"
            async with session.get(url, params={"symbol": symbol, "limit": limit}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = {
                        "symbol": symbol,
                        "bids": [[float(p), float(q)] for p, q in data["bids"][:20]],
                        "asks": [[float(p), float(q)] for p, q in data["asks"][:20]],
                    }
                    await cache_orderbook(symbol, result)
                    return result
    except Exception as e:
        logger.error("Failed to fetch orderbook", symbol=symbol, error=str(e))
    return None
