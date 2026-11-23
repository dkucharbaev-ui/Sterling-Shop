import re
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from bot.bot.states import OrderFlow
from bot.bot.db import (
    async_session, get_or_create_user, get_categories,
    get_products_by_category, get_product_by_id, get_user_orders,
    get_order_by_number, get_order_by_id, get_order_by_number_any_user,
)
from app.models.order import Order, OrderEvent, OrderStatus, PaymentProviderType
from app.services.recipient_check import recipient_check_service
from app.payments.service import payment_service, get_payment_provider
from app.fulfillment.service import fulfillment_service
from app.config import get_settings

settings = get_settings()
router = Router()

STAR_RUB_RATE = Decimal("1.65")
TON_RATE = Decimal("520.00")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{5,32}$")


def calc_product_price(product, quantity: int) -> Decimal:
    """Вычисляет цену товара."""
    if product.product_type == "STARS_CUSTOM" or "stars" in product.sku.lower():
        return (STAR_RUB_RATE * Decimal(str(quantity))).quantize(Decimal("0.01"))
    elif product.product_type == "VPN_SUBSCRIPTION":
        # Берём фиксированную цену из metadata_json
        meta = product.metadata_json or {}
        price_rub = meta.get("price_rub", 199.0)
        return Decimal(str(price_rub)).quantize(Decimal("0.01"))
    elif "premium-3m" in product.sku:
        return Decimal("1350.00")
    elif "premium-6m" in product.sku:
        return Decimal("2390.00")
    elif "premium-12m" in product.sku:
        return Decimal("4230.00")
    else:
        margin = Decimal(str(product.category.margin_percent))
        base = Decimal(str(product.base_price_ton))
        raw = base * Decimal(str(quantity)) * TON_RATE
        final = raw * (Decimal("1") + margin / Decimal("100"))
        return final.quantize(Decimal("0.01"))


def get_star_quick_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с быстрым выбором количества звёзд."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 100 шт. — 165₽", callback_data="star_qty:100"),
                InlineKeyboardButton(text="⭐ 250 шт. — 412.50₽", callback_data="star_qty:250"),
            ],
            [
                InlineKeyboardButton(text="⭐ 500 шт. — 825₽", callback_data="star_qty:500"),
                InlineKeyboardButton(text="⭐ 1 000 шт. — 1 650₽", callback_data="star_qty:1000"),
            ],
            [
                InlineKeyboardButton(text="⭐ 2 500 шт. — 4 125₽", callback_data="star_qty:2500"),
                InlineKeyboardButton(text="⭐ 5 000 шт. — 8 250₽", callback_data="star_qty:5000"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ],
        ]
    )


# ── Отмена заказа / процесса ──
@router.callback_query(F.data == "cancel")
async def cancel_flow(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    from bot.bot.main import main_menu_kb
    await cb.message.edit_text(
        "❌ Действие отменено.\n\nВыберите действие в главном меню 👇",
        reply_markup=main_menu_kb(),
    )


# ── Каталог ──
@router.callback_query(F.data == "catalog")
async def show_catalog_cb(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    async with async_session() as db:
        products = await get_products_by_category(db, "vpn")
    rows = []
    for p in products:
        price = calc_product_price(p, p.default_quantity)
        label = f"🛡 {p.name} — {price}₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"prod:{p.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await cb.message.edit_text(
        "🛡 <b>Тарифы VPN:</b>\n\n"
        "⚡ <b>Высокая скорость:</b> YouTube 4K, соцсети, стриминг без ограничений\n"
        "🔒 <b>Безопасность:</b> надёжное шифрование, строгий No-Logs\n"
        "📱 <b>Все устройства:</b> iOS, Android, Windows, macOS, Smart TV\n"
        "🌍 <b>Трафик:</b> безлимитный на всех тарифах\n\n"
        "Выберите желаемый период подписки 👇",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.set_state(OrderFlow.choosing_product)


@router.message(Command("catalog"))
async def cmd_catalog(message: types.Message, state: FSMContext):
    await state.clear()
    async with async_session() as db:
        products = await get_products_by_category(db, "vpn")
    rows = []
    for p in products:
        price = calc_product_price(p, p.default_quantity)
        label = f"🛡 {p.name} — {price}₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"prod:{p.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(
        "🛡 <b>Тарифы VPN:</b>\n\n"
        "⚡ <b>Высокая скорость:</b> YouTube 4K, соцсети, стриминг без ограничений\n"
        "🔒 <b>Безопасность:</b> надёжное шифрование, строгий No-Logs\n"
        "📱 <b>Все устройства:</b> iOS, Android, Windows, macOS, Smart TV\n"
        "🌍 <b>Трафик:</b> безлимитный на всех тарифах\n\n"
        "Выберите желаемый период подписки 👇",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.set_state(OrderFlow.choosing_product)


# ── Выбор категории ──
@router.callback_query(F.data.startswith("cat:"))
async def select_category(cb: types.CallbackQuery, state: FSMContext):
    slug = cb.data.split(":")[1]
    async with async_session() as db:
        products = await get_products_by_category(db, slug)
        if not products:
            await cb.answer("В этой категории пока нет товаров.", show_alert=True)
            return
        rows = []
        for p in products:
            if p.product_type == "STARS_CUSTOM":
                label = f"⭐ {p.name} — 1.65₽ / шт. (100 = 165₽)"
            else:
                price = calc_product_price(p, p.default_quantity)
                label = f"{p.name} — {price}₽"
            rows.append([InlineKeyboardButton(text=label, callback_data=f"prod:{p.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await cb.message.edit_text(
        "🛒 <b>Выберите нужный товар:</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.set_state(OrderFlow.choosing_product)


# ── Выбор товара ──
@router.callback_query(F.data.startswith("prod:"))
async def select_product(cb: types.CallbackQuery, state: FSMContext):
    pid = cb.data.split(":")[1]
    async with async_session() as db:
        product = await get_product_by_id(db, pid)
        if not product:
            await cb.answer("Товар не найден", show_alert=True)
            return
        pname = product.name
        ptype = product.product_type
        min_q = product.min_quantity or 50
        max_q = product.max_quantity or 100000

    await state.update_data(
        product_id=pid,
        product_name=pname,
        product_type=ptype,
        min_q=min_q,
        max_q=max_q,
    )

    if ptype == "STARS_CUSTOM" or "stars" in pname.lower():
        await cb.message.edit_text(
            f"⭐ <b>{pname}</b>\n\n"
            f"💡 Курс: <b>1.65₽</b> за 1 звезду (100 звёзд = <b>165₽</b>)\n"
            f"📦 Лимиты: от <b>{min_q}</b> до <b>{max_q:,}</b> звёзд\n\n"
            f"Выберите готовое количество или <b>отправьте число сообщением</b> в чат 👇",
            reply_markup=get_star_quick_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(OrderFlow.entering_quantity)
    elif ptype == "VPN_SUBSCRIPTION":
        price = calc_product_price(product, product.default_quantity)
        meta = product.metadata_json or {}
        months = meta.get("months", product.default_quantity)
        await state.update_data(quantity=product.default_quantity, price=str(price))
        rows = []
        if cb.from_user.username:
            rows.append([InlineKeyboardButton(
                text=f"👤 Оформить на себя (@{cb.from_user.username})",
                callback_data=f"recipient:{cb.from_user.username}",
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Выбрать другой тариф", callback_data="catalog")])
        rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        await cb.message.edit_text(
            f"🛡 <b>{pname}</b>\n"
            f"⏱ Срок: <b>{months} мес.</b>\n"
            f"💰 Стоимость: <b>{price}₽</b>\n"
            f"📱 Устройства: <b>Все (Android, iOS, Windows, Mac)</b>\n"
            f"🌍 Трафик: <b>Безлимит</b>\n\n"
            f"👤 Введите ваш <b>@username</b> (или нажмите кнопку ниже).\n"
            f"<i>VPN-ключ и инструкция будут отправлены вам после оплаты.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML",
        )
        await state.set_state(OrderFlow.entering_recipient)
    else:
        # Для Premium и остальных
        price = calc_product_price(product, product.default_quantity)
        await state.update_data(quantity=product.default_quantity, price=str(price))
        rows = []
        if cb.from_user.username:
            rows.append([InlineKeyboardButton(
                text=f"👤 Себе (@{cb.from_user.username})",
                callback_data=f"recipient:{cb.from_user.username}",
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Выбрать другой тариф", callback_data="catalog")])
        rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
        await cb.message.edit_text(
            f"💎 <b>{pname}</b>\n"
            f"💰 Стоимость: <b>{price}₽</b>\n\n"
            f"👤 Введите <b>@username</b> получателя подписки в чат (или нажмите кнопку ниже):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML",
        )
        await state.set_state(OrderFlow.entering_recipient)


# ── Быстрый выбор звёзд по кнопке ──
@router.callback_query(F.data.startswith("star_qty:"))
async def quick_star_qty_cb(cb: types.CallbackQuery, state: FSMContext):
    qty = int(cb.data.split(":")[1])
    price = (STAR_RUB_RATE * Decimal(str(qty))).quantize(Decimal("0.01"))
    await state.update_data(quantity=qty, price=str(price))

    rows = []
    if cb.from_user.username:
        rows.append([InlineKeyboardButton(
            text=f"👤 Отправить себе (@{cb.from_user.username})",
            callback_data=f"recipient:{cb.from_user.username}",
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Изменить количество", callback_data="cat:stars")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])

    await cb.message.edit_text(
        f"⭐ Выбрано: <b>{qty} звёзд</b>\n"
        f"💰 Сумма: <b>{price}₽</b> (по курсу 1.65₽ / шт.)\n\n"
        f"👤 Отправьте <b>@username</b> получателя сообщением в чат:\n"
        f"<i>(Пример: @durov или без знака @)</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await state.set_state(OrderFlow.entering_recipient)


# ── Ввод количества звёзд сообщением ──
@router.message(OrderFlow.entering_quantity)
async def enter_quantity_message(msg: types.Message, state: FSMContext):
    text = (msg.text or "").strip()
    if text.startswith("/"):
        if text in ["/cancel", "/stop"]:
            await state.clear()
            from bot.bot.main import main_menu_kb
            await msg.answer("❌ Заказ отменён.", reply_markup=main_menu_kb())
            return

    try:
        qty = int(text)
    except ValueError:
        await msg.answer(
            "❌ Пожалуйста, введите количество <b>числом</b> (например: <code>100</code>) "
            "или выберите вариант из кнопок выше 👆",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    min_q = data.get("min_q", 50)
    max_q = data.get("max_q", 100000)

    if qty < min_q or qty > max_q:
        await msg.answer(
            f"❌ Количество должно быть от <b>{min_q}</b> до <b>{max_q:,}</b> звёзд.\n"
            f"Попробуйте ещё раз:",
            parse_mode="HTML",
        )
        return

    price = (STAR_RUB_RATE * Decimal(str(qty))).quantize(Decimal("0.01"))
    await state.update_data(quantity=qty, price=str(price))

    rows = []
    if msg.from_user and msg.from_user.username:
        rows.append([InlineKeyboardButton(
            text=f"👤 Отправить себе (@{msg.from_user.username})",
            callback_data=f"recipient:{msg.from_user.username}",
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])

    await msg.answer(
        f"⭐ Выбрано: <b>{qty} звёзд</b>\n"
        f"💰 Итоговая стоимость: <b>{price}₽</b> (по 1.65₽ / шт.)\n\n"
        f"👤 Введите <b>@username</b> получателя (кому доставить звёзды):\n"
        f"<i>(Пример: @username или выберите кнопку ниже)</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await state.set_state(OrderFlow.entering_recipient)


# ── Выбор получателя кнопкой ──
@router.callback_query(F.data.startswith("recipient:"))
async def recipient_from_button_cb(cb: types.CallbackQuery, state: FSMContext):
    clean_username = cb.data.split(":")[1].strip().lstrip("@")
    await process_valid_recipient(clean_username, cb.message, state, is_edit=True)


# ── Ввод получателя текстом ──
@router.message(OrderFlow.entering_recipient)
async def enter_recipient_message(msg: types.Message, state: FSMContext):
    text = (msg.text or "").strip()
    if text.startswith("/"):
        if text in ["/cancel", "/stop"]:
            await state.clear()
            from bot.bot.main import main_menu_kb
            await msg.answer("❌ Заказ отменён.", reply_markup=main_menu_kb())
            return

    clean_username = text.lstrip("@").strip()
    if not USERNAME_REGEX.match(clean_username):
        await msg.answer(
            "❌ Некорректный username получателя.\n"
            "Имя пользователя должно состоять из латинских букв, цифр и _ (от 5 до 32 символов).\n"
            "Попробуйте ещё раз:",
            parse_mode="HTML",
        )
        return

    await process_valid_recipient(clean_username, msg, state, is_edit=False)


async def process_valid_recipient(clean_username: str, target_message, state: FSMContext, is_edit: bool = False):
    await state.update_data(recipient=clean_username)
    data = await state.get_data()
    pname = data.get("product_name", "Товар")
    qty = data.get("quantity", 1)
    price = Decimal(data.get("price", "165.00"))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 CryptoBot (криптовалюта)", callback_data="pay:CRYPTOBOT")],
            [InlineKeyboardButton(text="💳 Lava Pay (карта РФ / СБП)", callback_data="pay:LAVAPAY")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )

    text = (
        f"📋 <b>Детали заказа:</b>\n\n"
        f"🛒 Товар: <b>{pname}</b>\n"
        f"📦 Количество: <b>{qty}</b>\n"
        f"👤 Получатель: <b>@{clean_username}</b>\n"
        f"💰 К оплате: <b>{price}₽</b>\n\n"
        f"Выберите удобный способ оплаты 👇"
    )

    if is_edit:
        await target_message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target_message.answer(text, reply_markup=kb, parse_mode="HTML")

    await state.set_state(OrderFlow.choosing_payment)


# ── Выбор способа оплаты → Экран подтверждения ──
@router.callback_query(F.data.startswith("pay:"))
async def select_payment_method(cb: types.CallbackQuery, state: FSMContext):
    provider_str = cb.data.split(":")[1]
    provider_label = "CryptoBot (криптовалюта)" if provider_str == "CRYPTOBOT" else "Lava Pay (карты РФ / СБП)"
    data = await state.get_data()
    pname = data.get("product_name", "Товар")
    qty = data.get("quantity", 1)
    price = Decimal(data.get("price", "165.00"))
    recipient = data.get("recipient", "друг")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оформить и оплатить", callback_data=f"confirm:{provider_str}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )

    await cb.message.edit_text(
        f"📋 <b>Подтверждение заказа:</b>\n\n"
        f"🛒 Товар: <b>{pname}</b>\n"
        f"⭐ Количество: <b>{qty} шт.</b>\n"
        f"👤 Получатель: <b>@{recipient}</b>\n"
        f"💳 Оплата: <b>{provider_label}</b>\n"
        f"💵 Сумма к оплате: <b>{price}₽</b>\n\n"
        f"Нажмите кнопку <b>«✅ Оформить и оплатить»</b> для перехода к оплате.",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.set_state(OrderFlow.confirming)


# ── Создание заказа и инвойса ──
@router.callback_query(F.data.startswith("confirm:"))
async def confirm_order(cb: types.CallbackQuery, state: FSMContext):
    provider_str = cb.data.split(":")[1]
    provider = PaymentProviderType(provider_str)
    provider_label = "CryptoBot" if provider == PaymentProviderType.CRYPTOBOT else "Lava Pay"
    data = await state.get_data()
    price = Decimal(data.get("price", "165.00"))
    qty = int(data.get("quantity", 100))
    recipient = data.get("recipient", cb.from_user.username or "user")
    pid = data.get("product_id")

    await cb.message.edit_text("⏳ Формируем заказ и платёжную ссылку...")

    try:
        async with async_session() as db:
            user = await get_or_create_user(db, cb.from_user)
            product = await get_product_by_id(db, pid)
            if not product:
                raise ValueError("Товар не найден в базе данных")

            from sqlalchemy import func, select as sa_select
            last_num = (await db.execute(sa_select(func.coalesce(func.max(Order.order_number), 100000)))).scalar_one()
            new_num = last_num + 1
            now = datetime.now(timezone.utc)

            order = Order(
                order_number=new_num,
                user_id=user.id,
                product_id=product.id,
                quantity=qty,
                recipient_username=recipient,
                is_gift=(recipient.lower() != (cb.from_user.username or "").lower()),
                status=OrderStatus.CREATED,
                payment_provider=provider,
                fiat_amount=price,
                fiat_currency="RUB",
                ton_rate_applied=TON_RATE,
                expires_at=now + timedelta(minutes=15),
            )
            db.add(order)
            await db.flush()

            event = OrderEvent(
                order_id=order.id,
                from_status=None,
                to_status=OrderStatus.CREATED,
                event_type="ORDER_CREATED",
                details={"quantity": qty, "price": str(price), "recipient": recipient},
            )
            db.add(event)
            await db.commit()
            await db.refresh(order)

            # Генерация платёжного инвойса
            invoice_id, payment_url = await payment_service.initialize_payment(db, order)
            order_id_str = str(order.id)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"💳 Оплатить {price}₽", url=payment_url)],
                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_order:{order_id_str}")],
                [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
                [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order:{order_id_str}")],
            ]
        )

        # Текст зависит от типа товара
        if product.product_type == "VPN_SUBSCRIPTION":
            after_pay_hint = "После оплаты нажмите <b>«🔄 Проверить оплату»</b> — VPN-ключ и инструкция придут в этот чат."
        elif product.product_type == "STARS_CUSTOM":
            after_pay_hint = "После оплаты нажмите <b>«🔄 Проверить оплату»</b> — звёзды будут начислены автоматически."
        else:
            after_pay_hint = "После оплаты нажмите <b>«🔄 Проверить оплату»</b> — Premium будет активирован автоматически."

        await cb.message.edit_text(
            f"✅ <b>Заказ #{new_num} успешно оформлен!</b>\n\n"
            f"🛒 Товар: <b>{product.name}</b>\n"
            f"👤 Получатель: <b>@{recipient}</b>\n"
            f"💰 Сумма к оплате: <b>{price}₽</b>\n"
            f"💳 Провайдер: <b>{provider_label}</b>\n"
            f"⏰ Счёт активен: <b>15 минут</b>\n\n"
            f"👇 Нажмите <b>«Оплатить»</b> для перехода к оплате.\n"
            f"{after_pay_hint}",
            reply_markup=kb,
            parse_mode="HTML",
        )

    except Exception as e:
        from bot.bot.main import main_menu_kb
        await cb.message.edit_text(
            f"❌ Ошибка создания счёта:\n<code>{e}</code>\n\nПопробуйте снова позже.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )

    await state.clear()


# ── Проверка статуса оплаты и автовыдача ──
@router.callback_query(F.data.startswith("check_order:"))
async def check_order_status(cb: types.CallbackQuery):
    order_id = cb.data.split(":")[1]

    async with async_session() as db:
        order = await get_order_by_id(db, order_id)
        if not order:
            await cb.answer("❌ Заказ не найден", show_alert=True)
            return

        if order.status == OrderStatus.COMPLETED:
            await cb.answer("✅ Заказ уже успешно оплачен и выполнен!", show_alert=True)
            return

        # Проверяем статус в API платежного провайдера
        try:
            provider = get_payment_provider(order.payment_provider)
            status_res = await provider.get_invoice_status(order.payment_invoice_id)
        except Exception as e:
            await cb.answer(f"Ошибка связи с платёжным шлюзом: {e}", show_alert=True)
            return

        if status_res.is_paid:
            # Оплата подтверждена! Запускаем доставку
            order.status = OrderStatus.PAID
            await db.commit()

            success = await fulfillment_service.execute_order_fulfillment(db, order)
            if success:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🛒 В каталог", callback_data="catalog")],
                        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
                    ]
                )
                # Текст зависит от типа товара
                ptype = order.product.product_type if order.product else "STARS_CUSTOM"
                if ptype == "VPN_SUBSCRIPTION":
                    success_text = (
                        f"🎉 <b>Оплата подтверждена!</b>\n\n"
                        f"✅ Заказ <b>#{order.order_number}</b> оформлен!\n"
                        f"🛡 Товар: <b>{order.product.name}</b>\n"
                        f"👤 Аккаунт: <b>@{order.recipient_username}</b>\n\n"
                        f"⏳ <b>VPN-ключ и инструкция по подключению будут отправлены "
                        f"вам в этот чат в течение нескольких минут.</b>\n\n"
                        f"Если ключ не пришёл через 15 минут — напишите в поддержку 👇"
                    )
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="💬 Поддержка", url="tg://user?id=5996360364")],
                            [InlineKeyboardButton(text="🛒 В каталог", callback_data="catalog")],
                        ]
                    )
                elif ptype == "PREMIUM_MONTHS":
                    success_text = (
                        f"🎉 <b>Оплата подтверждена!</b>\n\n"
                        f"✅ Заказ <b>#{order.order_number}</b> выполнен!\n"
                        f"💎 <b>Telegram Premium</b> активирован для <b>@{order.recipient_username}</b>!\n"
                        f"📦 Хэш: <code>{order.fulfillment_tx_hash}</code>\n\n"
                        f"Спасибо за покупку! 💎"
                    )
                else:
                    success_text = (
                        f"🎉 <b>Оплата подтверждена!</b>\n\n"
                        f"✅ Заказ <b>#{order.order_number}</b> выполнен!\n"
                        f"⭐ <b>{order.quantity} звёзд</b> начислены <b>@{order.recipient_username}</b>!\n"
                        f"📦 Хэш: <code>{order.fulfillment_tx_hash}</code>\n\n"
                        f"Спасибо за покупку в Ska1L Stars! ⭐"
                    )
                await cb.message.edit_text(success_text, reply_markup=kb, parse_mode="HTML")
                return
            else:
                await cb.message.edit_text(
                    f"⚠️ <b>Оплата принята, но возникла задержка при начислении звёзд.</b>\n\n"
                    f"Номер заказа: <b>#{order.order_number}</b>\n"
                    f"Статус: <code>{order.status.value}</code>\n"
                    f"Ошибка: {order.fulfillment_error}\n\n"
                    f"Пожалуйста, обратитесь в поддержку — заказ будет выдан вручную.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="💬 Поддержка", url="tg://user?id=5996360364")],
                        ]
                    ),
                    parse_mode="HTML",
                )
                return
        else:
            await cb.answer(
                "⏳ Платёж ещё не поступил.\nЕсли вы только что оплатили, подождите 15–30 секунд и нажмите снова.",
                show_alert=True,
            )


# ── Отмена конкретного заказа ──
@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_specific_order(cb: types.CallbackQuery):
    order_id = cb.data.split(":")[1]
    async with async_session() as db:
        order = await get_order_by_id(db, order_id)
        if order and order.status in [OrderStatus.CREATED, OrderStatus.AWAITING_PAYMENT]:
            order.status = OrderStatus.CANCELLED
            await db.commit()
            await cb.answer("Заказ отменён", show_alert=True)
            from bot.bot.main import main_menu_kb
            await cb.message.edit_text(f"🚫 Заказ #{order.order_number} был отменён.", reply_markup=main_menu_kb())
        else:
            await cb.answer("Невозможно отменить этот заказ", show_alert=True)


# ── Мои заказы ──
@router.callback_query(F.data == "my_orders")
async def show_orders(cb: types.CallbackQuery):
    async with async_session() as db:
        orders = await get_user_orders(db, cb.from_user.id)

    if not orders:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🛒 В каталог", callback_data="catalog")]]
        )
        await cb.message.edit_text("📭 У вас пока нет оформленных заказов.", reply_markup=kb)
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
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")])

    text = "📋 <b>Ваши последние заказы:</b>\n\n" + "\n\n".join(lines)
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


# ── Админ-команда для мгновенного теста выдачи без реальной оплаты ──
@router.message(Command("testpay"))
async def admin_testpay_cmd(message: types.Message):
    """
    /testpay <номер_заказа> — мгновенно имитирует успешную оплату и запускает
    процесс доставки звёзд получателю (доступно только админу).
    """
    admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Команда доступна только администраторам.")
        return

    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/testpay 100001</code> (укажите номер заказа)", parse_mode="HTML")
        return

    order_num = int(parts[1])
    async with async_session() as db:
        order = await get_order_by_number_any_user(db, order_num)
        if not order:
            await message.answer(f"❌ Заказ #{order_num} не найден.")
            return

        order.status = OrderStatus.PAID
        await db.commit()

        success = await fulfillment_service.execute_order_fulfillment(db, order)
        if success:
            await message.answer(
                f"🎉 <b>[ТЕСТ] Заказ #{order.order_number} успешно выдан!</b>\n\n"
                f"⭐ Товар: {order.product.name} × {order.quantity}\n"
                f"👤 Получатель: @{order.recipient_username}\n"
                f"📦 Хэш транзакции: <code>{order.fulfillment_tx_hash}</code>\n"
                f"Статус: <b>{order.status.value}</b>",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"❌ [ТЕСТ] Заказ #{order.order_number}: ошибка доставки: {order.fulfillment_error}",
                parse_mode="HTML",
            )
