"""Redis client factory used for caching, rate limiting and distributed locks."""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    """Return a cached async Redis client bound to the process lifetime."""
    settings = get_settings()
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)
