import asyncio
import json
import math
import time
import aiohttp
from typing import Optional, Dict, List
from app.core.config import settings
from app.db.redis import cache_price, get_cached_price, cache_orderbook, get_cached_orderbook
import structlog

logger = structlog.get_logger()

_price_cache: Dict[str, float] = {}

# Realistic mock prices used when Binance is unreachable
_MOCK_BASE_PRICES: Dict[str, float] = {
    "BTCUSDT": 87432.50, "ETHUSDT": 3124.80, "BNBUSDT": 612.40,
    "SOLUSDT": 178.42, "XRPUSDT": 0.5821, "ADAUSDT": 0.4512,
    "DOGEUSDT": 0.1823, "AVAXUSDT": 34.76, "DOTUSDT": 6.94,
    "MATICUSDT": 0.8732, "LINKUSDT": 14.23, "UNIUSDT": 8.45,
    "LTCUSDT": 92.18, "ATOMUSDT": 8.91, "XLMUSDT": 0.1124,
}
_MOCK_CHANGE_PCT: Dict[str, float] = {
    "BTCUSDT": 2.34, "ETHUSDT": -1.12, "BNBUSDT": 0.87,
    "SOLUSDT": 5.63, "XRPUSDT": -0.45, "ADAUSDT": 1.28,
    "DOGEUSDT": 3.91, "AVAXUSDT": -2.17, "DOTUSDT": 0.55,
    "MATICUSDT": -1.89, "LINKUSDT": 4.32, "UNIUSDT": -0.73,
    "LTCUSDT": 1.14, "ATOMUSDT": -3.05, "XLMUSDT": 0.62,
}


def _mock_ticker(symbol: str) -> dict:
    """Generate a realistic mock ticker for a symbol."""
    base = _MOCK_BASE_PRICES.get(symbol, 100.0)
    # add subtle time-based drift so prices aren't perfectly static
    drift = math.sin(time.time() / 60 + hash(symbol) % 10) * base * 0.002
    price = round(base + drift, 6 if base < 1 else 2)
    pct = _MOCK_CHANGE_PCT.get(symbol, 0.0)
    change = round(price * pct / 100, 6 if base < 1 else 2)
    return {
        "symbol": symbol,
        "price": price,
        "change_24h": change,
        "change_percent_24h": pct,
        "high_24h": round(price * 1.03, 2),
        "low_24h": round(price * 0.97, 2),
        "volume_24h": round(base * 12000, 2),
        "quote_volume_24h": round(base * price * 12000, 2),
    }


async def fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch current price from cache or Binance API, falling back to mock data."""
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
        logger.warning("Binance unreachable, using mock price", symbol=symbol, error=str(e))

    # Fallback: mock price
    price = _mock_ticker(symbol)["price"]
    _price_cache[symbol] = price
    return price


async def fetch_ticker_24h(symbol: str) -> Optional[dict]:
    """Fetch 24h ticker stats from Binance, falling back to mock data."""
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
        logger.warning("Binance unreachable, using mock ticker", symbol=symbol, error=str(e))
    return _mock_ticker(symbol)


async def fetch_all_tickers() -> List[dict]:
    """Fetch tickers for all supported pairs, falling back to mock data."""
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
        logger.warning("Binance unreachable, using mock tickers", error=str(e))
    # Fallback: return mock data for all supported pairs
    return [_mock_ticker(sym) for sym in settings.SUPPORTED_PAIRS]


def _mock_klines(symbol: str, limit: int = 200) -> List[dict]:
    """Generate realistic mock candlestick data."""
    base = _MOCK_BASE_PRICES.get(symbol, 100.0)
    now_ms = int(time.time() * 1000)
    interval_ms = 3600_000  # 1h
    candles = []
    price = base
    for i in range(limit):
        ts = now_ms - (limit - i) * interval_ms
        change = (math.sin(i * 0.3 + hash(symbol) % 5) + 0.05) * base * 0.01
        open_p = round(price, 2)
        close_p = round(price + change, 2)
        high_p = round(max(open_p, close_p) * 1.005, 2)
        low_p = round(min(open_p, close_p) * 0.995, 2)
        candles.append({
            "time": ts, "open": open_p, "high": high_p,
            "low": low_p, "close": close_p,
            "volume": round(base * 500 + i * 10, 2),
            "close_time": ts + interval_ms - 1,
        })
        price = close_p
    return candles


async def fetch_klines(symbol: str, interval: str = "1h", limit: int = 200) -> List[dict]:
    """Fetch candlestick data from Binance, falling back to mock data."""
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
        logger.warning("Binance unreachable, using mock klines", symbol=symbol, error=str(e))
    return _mock_klines(symbol, limit)


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
