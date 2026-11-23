from typing import Any, Dict
from arq.connections import RedisSettings
from app.config import get_settings
from app.core.logger import logger, setup_logging

settings = get_settings()


async def ping_task(ctx: Dict[str, Any], message: str) -> str:
    logger.info("ping_task_executed", message=message)
    return f"pong: {message}"


async def startup(ctx: Dict[str, Any]) -> None:
    setup_logging(settings.DEBUG)
    logger.info("arq_worker_started")


async def shutdown(ctx: Dict[str, Any]) -> None:
    logger.info("arq_worker_stopped")


class WorkerSettings:
    functions = [ping_task]
    on_startup = startup
    on_shutdown = shutdown
    # Parse redis url
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    poll_delay = 0.5
