import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SterlingStarBot")
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("psycho_bot")

menu_router = Router()
fallback_router = Router()


TERMS_URL = "https://telegra.ph/Polzovatelskoe-soglashenie-11-17-65"
PRIVACY_URL = "https://telegra.ph/Politiki-konfidencialnosti-11-17"


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛡 Оформить VPN", callback_data="catalog")],
            [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
            [InlineKeyboardButton(text="ℹ️ Помощь и тарифы", callback_data="help")],
            [InlineKeyboardButton(text="💬 Поддержка", url="tg://user?id=5996360364")],
            [
                InlineKeyboardButton(text="📄 Соглашение", url=TERMS_URL),
                InlineKeyboardButton(text="🔒 Конфиденциальность", url=PRIVACY_URL),
            ],
        ]
    )


# ── Команда /start ──
@menu_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"Добро пожаловать в <b>Sterling Shop</b> — быстрый и безопасный <b>VPN</b> для всех ваших устройств.\n\n"
        f"⚡ <b>Скорость:</b> безлимитный трафик, YouTube 4K, соцсети\n"
        f"🔒 <b>Приватность:</b> надёжное шифрование, без ведения логов\n"
        f"📱 <b>Совместимость:</b> iOS, Android, Windows, macOS, Smart TV\n"
        f"💳 <b>Оплата:</b> Карты РФ, СБП (Lava Pay) и Криптовалюта (CryptoBot)\n\n"
        f"Используя бота, вы принимаете <a href='{TERMS_URL}'>Пользовательское соглашение</a> "
        f"и <a href='{PRIVACY_URL}'>Политику конфиденциальности</a>.\n\n"
        f"Нажмите кнопку ниже, чтобы выбрать тариф 👇",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── Команда /cancel ──
@menu_router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu_kb())


# ── Команда /help ──
@menu_router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 <b>Команды бота:</b>\n\n"
        "/start — Главное меню\n"
        "/catalog — Тарифы VPN\n"
        "/orders — Список ваших заказов\n"
        "/cancel — Отменить текущее действие\n"
        "/status — Проверить статус работы бота\n\n"
        "💬 Поддержка: нажмите кнопку ниже для связи с администратором.\n\n"
        f"📄 <a href='{TERMS_URL}'>Пользовательское соглашение</a>\n"
        f"🔒 <a href='{PRIVACY_URL}'>Политика конфиденциальности</a>",
        reply_markup=main_menu_kb(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── Callback "Помощь" ──
@menu_router.callback_query(F.data == "help")
async def cb_help(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "📖 <b>Как оформить VPN:</b>\n\n"
        "1️⃣ Нажмите <b>«🛡 Оформить VPN»</b>\n"
        "2️⃣ Выберите подходящий тариф (1, 3, 6 или 12 месяцев)\n"
        "3️⃣ Укажите ваш @username\n"
        "4️⃣ Выберите способ оплаты (Карты РФ / СБП или Крипта)\n"
        "5️⃣ Оплатите по ссылке и нажмите <b>«🔄 Проверить оплату»</b>\n"
        "6️⃣ VPN-ключ и инструкция будут отправлены вам в этот чат!\n\n"
        f"📄 <a href='{TERMS_URL}'>Пользовательское соглашение</a>\n"
        f"🔒 <a href='{PRIVACY_URL}'>Политика конфиденциальности</a>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 Соглашение", url=TERMS_URL),
                    InlineKeyboardButton(text="🔒 Конфиденциальность", url=PRIVACY_URL),
                ],
                [InlineKeyboardButton(text="🛡 Оформить VPN", callback_data="catalog")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
            ]
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ── Callback "Главное меню" ──
@menu_router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    name = cb.from_user.first_name if cb.from_user else "друг"
    await cb.message.edit_text(
        f"👋 <b>{name}</b>, выберите нужное действие 👇",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ── Команда /orders ──
@menu_router.message(Command("orders"))
async def cmd_orders(message: types.Message):
    from bot.bot.db import async_session, get_user_orders
    from app.models.order import OrderStatus

    async with async_session() as db:
        orders = await get_user_orders(db, message.from_user.id)

    if not orders:
        await message.answer(
            "📭 У вас пока нет оформленных заказов.\n\nНажмите кнопку ниже, чтобы перейти в каталог 👇",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🛒 В каталог", callback_data="catalog")]]
            ),
        )
        return

    status_emoji = {
        "CREATED": "🆕",
        "AWAITING_PAYMENT": "⏳ Ожидает оплаты",
        "PAID": "✅ Оплачен",
        "FULFILLING": "🔄 Доставляется",
        "COMPLETED": "🎉 Выполнен",
        "FAILED": "❌ Ошибка",
        "CANCELLED": "🚫 Отменён",
        "REFUNDED": "💸 Возврат",
    }

    lines = []
    rows = []
    for o in orders:
        emoji_st = status_emoji.get(o.status.value, o.status.value)
        pname = o.product.name if o.product else "Товар"
        lines.append(
            f"<b>Заказ #{o.order_number}</b>\n"
            f"  • {pname} × {o.quantity}\n"
            f"  • Получатель: @{o.recipient_username}\n"
            f"  • Сумма: {o.fiat_amount}₽ ({o.payment_provider.value})\n"
            f"  • Статус: {emoji_st}"
        )
        if o.status == OrderStatus.AWAITING_PAYMENT and o.payment_url:
            rows.append([
                InlineKeyboardButton(text=f"💳 Оплатить #{o.order_number}", url=o.payment_url),
                InlineKeyboardButton(text="🔄 Проверить", callback_data=f"check_order:{o.id}"),
            ])

    rows.append([InlineKeyboardButton(text="🛒 В каталог", callback_data="catalog")])

    text = "📋 <b>Ваши последние заказы:</b>\n\n" + "\n\n".join(lines)
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── Команда /status ──
@menu_router.message(Command("status"))
async def cmd_status(message: types.Message):
    await message.answer(
        "🟢 <b>Бот работает в штатном режиме</b>\n\n"
        "⚡ <b>Платёжные шлюзы:</b> CryptoBot & Lava Pay (подключены)\n"
        "⭐ <b>Курс:</b> 1.65₽ за 1 звезду\n"
        "📦 <b>Доставка звёзд:</b> активна",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── Fallback для неизвестных сообщений вне FSM-состояний ──
@fallback_router.message(StateFilter(None), F.text)
async def fallback_unknown_text(message: types.Message):
    await message.answer(
        "🤔 Я не понял эту команду.\n\n"
        "Используйте кнопки меню ниже или команду /start 👇",
        reply_markup=main_menu_kb(),
    )


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан!")
        return

    # 1. Инициализация базы данных и каталога
    from bot.bot.db import init_db
    await init_db()
    logger.info("База данных проверена и готова к работе")

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 2. Подключение роутеров в строгом порядке:
    #    Каталог и FSM-обработчики ДОЛЖНЫ быть первыми,
    #    а fallback для вне-FSM сообщений — в самом конце!
    from bot.bot.handlers.catalog import router as catalog_router
    dp.include_router(catalog_router)
    dp.include_router(menu_router)
    dp.include_router(fallback_router)

    session = AiohttpSession()
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # 3. Сброс зависших вебхуков
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    logger.info(f"Бот запущен: @{me.username} (ID: {me.id})")

    try:
        await dp.start_polling(bot, polling_timeout=20)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
