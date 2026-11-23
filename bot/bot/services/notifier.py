import logging
from decimal import Decimal
from typing import List, Optional
from aiogram import Bot

logger = logging.getLogger("psycho_bot.notifier")


async def notify_customer_order_completed(
    bot: Bot,
    user_id: int,
    order_number: int,
    recipient: str,
    tx_hash: Optional[str] = None,
) -> None:
    msg = (
        f"🎉 <b>Заказ #{order_number} успешно выполнен!</b>\n\n"
        f"Товар отправлен на аккаунт: @{recipient}\n"
    )
    if tx_hash:
        msg += f"Хеш транзакции TON: <code>{tx_hash}</code>\n"
    msg += "\nСпасибо за покупку в Psycho Stars! ⭐"

    try:
        await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to send customer notification: {e}")


async def alert_admins_refund_pending(
    bot: Bot,
    admin_ids: List[int],
    order_number: int,
    recipient: str,
    error: str,
) -> None:
    alert_text = (
        f"🚨 <b>ВНИМАНИЕ: Сбой выдачи заказа #{order_number}!</b>\n\n"
        f"Получатель: @{recipient}\n"
        f"Ошибка Fragment: <code>{error}</code>\n"
        f"Статус: <b>REFUND_PENDING</b>\n\n"
        f"Пожалуйста, проверьте баланс или выполните ручной возврат в админ-панели."
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=alert_text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to alert admin {admin_id}: {e}")


async def alert_admins_low_balance(
    bot: Bot,
    admin_ids: List[int],
    current_balance: Decimal,
    threshold: float,
) -> None:
    alert_text = (
        f"⚠️ <b>Низкий баланс TON-кошелька магазина!</b>\n\n"
        f"Текущий баланс: <b>{current_balance} TON</b>\n"
        f"Порог предупреждения: {threshold} TON\n\n"
        f"Пополните кошелек для бесперебойной выдачи товаров!"
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=alert_text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to alert admin {admin_id}: {e}")
