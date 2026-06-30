import os
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_pool = None

async def get_redis():
    global _pool
    if _pool is None:
        try:
            _pool = aioredis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
            r = aioredis.Redis(connection_pool=_pool)
            await r.ping()
            return r
        except Exception:
            _pool = None
            return None
    try:
        r = aioredis.Redis(connection_pool=_pool)
        await r.ping()
        return r
    except Exception:
        _pool = None
        return None

async def rate_limit(ip: str, limit: int, window: int = 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    r = await get_redis()
    if r is None:
        return None  # Redis unavailable, fall back to in-memory
    key = f"rate:{ip}"
    now = int(__import__("time").time())
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    _, _, count, _ = await pipe.execute()
    return count <= limit
