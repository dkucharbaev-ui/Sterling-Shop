import asyncio
import logging
from typing import List
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiolimiter import AsyncLimiter

logger = logging.getLogger("psycho_bot.broadcaster")

# Strict 25 messages per second rate limit to prevent Telegram 429 FloodWait
rate_limiter = AsyncLimiter(max_rate=25, time_period=1.0)


async def send_message_with_rate_limit(
    bot: Bot,
    user_id: int,
    text: str,
) -> bool:
    async with rate_limiter:
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
            return True
        except TelegramRetryAfter as e:
            logger.warning(f"FloodWait hit: sleeping for {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            return await send_message_with_rate_limit(bot, user_id, text)
        except TelegramForbiddenError:
            logger.info(f"User {user_id} has blocked the bot")
            return False
        except Exception as e:
            logger.error(f"Failed to deliver message to {user_id}: {e}")
            return False


async def broadcast_message(
    bot: Bot,
    user_ids: List[int],
    text: str,
) -> int:
    """
    Broadcasts message across all users within strict 25 msg/s rate limit.
    Returns count of successfully delivered messages.
    """
    delivered = 0
    for uid in user_ids:
        success = await send_message_with_rate_limit(bot, uid, text)
        if success:
            delivered += 1
    return delivered
