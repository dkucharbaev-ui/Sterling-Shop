from typing import Optional
from redis.asyncio import ConnectionPool, Redis
from app.config import get_settings
from app.core.logger import logger

settings = get_settings()

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    global _redis_pool, _redis_client
    if _redis_client is None:
        try:
            _redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20,
            )
            _redis_client = Redis(connection_pool=_redis_pool)
            await _redis_client.ping()
            logger.info("redis_connected", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    return _redis_client


async def close_redis() -> None:
    global _redis_pool, _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
    logger.info("redis_disconnected")


async def get_redis() -> Optional[Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            return await init_redis()
        except Exception:
            return None
    return _redis_client
