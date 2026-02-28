import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = None


async def get_redis() -> aioredis.Redis:
    return redis_client


async def init_redis():
    global redis_client
    redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()


async def cache_price(symbol: str, price: float, ttl: int = 5):
    if redis_client:
        await redis_client.setex(f"price:{symbol}", ttl, str(price))


async def get_cached_price(symbol: str) -> float | None:
    if redis_client:
        val = await redis_client.get(f"price:{symbol}")
        return float(val) if val else None
    return None


async def cache_orderbook(symbol: str, data: dict, ttl: int = 2):
    import json
    if redis_client:
        await redis_client.setex(f"orderbook:{symbol}", ttl, json.dumps(data))


async def get_cached_orderbook(symbol: str) -> dict | None:
    import json
    if redis_client:
        val = await redis_client.get(f"orderbook:{symbol}")
        return json.loads(val) if val else None
    return None
