import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.catalog import Category, Product
from app.models.order import Order, OrderEvent, OrderStatus, PaymentProviderType
from app.models.user import User
from app.schemas.order import CreateOrderRequest
from app.services.pricing import pricing_service
from app.services.recipient_check import recipient_check_service

MAX_UNPAID_ORDERS_PER_USER = 3
ORDER_TIMEOUT_MINUTES = 15


class OrderService:
    async def create_order(
        self,
        db: AsyncSession,
        user: User,
        payload: CreateOrderRequest,
    ) -> Order:
        """
        Creates an order with full validation, anti-spam check, pricing calculation,
        and transaction event logging.
        """
        # 1. Anti-spam check: prevent excessive pending orders
        unpaid_count_query = select(func.count(Order.id)).where(
            Order.user_id == user.id,
            Order.status.in_([OrderStatus.CREATED, OrderStatus.AWAITING_PAYMENT]),
            Order.expires_at > datetime.now(timezone.utc),
        )
        unpaid_count = (await db.execute(unpaid_count_query)).scalar_one()
        if unpaid_count >= MAX_UNPAID_ORDERS_PER_USER:
            raise ValueError(
                f"У вас уже есть {unpaid_count} активных неоплаченных заказов. "
                "Пожалуйста, оплатите или дождитесь отмены предыдущих заказов."
            )

        # 2. Fetch product & category
        prod_query = select(Product).options(selectinload(Product.category)).where(
            Product.id == payload.product_id,
            Product.is_active.is_(True),
        )
        product = (await db.execute(prod_query)).scalar_one_or_none()
        if not product or not product.category or not product.category.is_active:
            raise ValueError("Выбранный товар недоступен для покупки.")

        # 3. Validate quantity limits
        if product.min_quantity and payload.quantity < product.min_quantity:
            raise ValueError(f"Минимальное количество для покупки: {product.min_quantity}")
        if product.max_quantity and payload.quantity > product.max_quantity:
            raise ValueError(f"Максимальное количество для покупки: {product.max_quantity}")

        # 4. Check recipient username & Telegram Premium status
        is_premium_product = "PREMIUM" in product.product_type
        recipient_check = await recipient_check_service.validate_recipient(
            raw_username=payload.recipient_username,
            is_premium_product=is_premium_product,
        )
        if not recipient_check.is_valid:
            raise ValueError(recipient_check.error_message or "Неверный username получателя.")

        # 5. Calculate price using pricing service (TON base * TON rate + margin)
        base_price_ton = Decimal(str(product.base_price_ton))
        margin_percent = Decimal(str(product.category.margin_percent))
        
        ton_rate, final_fiat_price = pricing_service.calculate_price(
            base_price_ton=base_price_ton,
            quantity=payload.quantity,
            margin_percent=margin_percent,
            target_currency=payload.currency,
        )

        # 6. Generate order number
        last_number_query = select(func.coalesce(func.max(Order.order_number), 100000))
        last_number = (await db.execute(last_number_query)).scalar_one()
        new_order_number = last_number + 1

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=ORDER_TIMEOUT_MINUTES)

        # 7. Create Order instance
        order = Order(
            order_number=new_order_number,
            user_id=user.id,
            product_id=product.id,
            quantity=payload.quantity,
            recipient_username=recipient_check.clean_username,
            is_gift=payload.is_gift,
            status=OrderStatus.CREATED,
            payment_provider=payload.payment_provider,
            fiat_amount=final_fiat_price,
            fiat_currency=payload.currency.upper(),
            ton_rate_applied=ton_rate,
            expires_at=expires_at,
        )
        db.add(order)
        await db.flush()

        # 8. Record initial lifecycle event
        event = OrderEvent(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.CREATED,
            event_type="ORDER_CREATED",
            details={
                "quantity": payload.quantity,
                "price": str(final_fiat_price),
                "currency": payload.currency,
                "recipient": recipient_check.clean_username,
                "ton_rate": str(ton_rate),
            },
        )
        db.add(event)
        await db.commit()
        await db.refresh(order)

        logger.info(
            "order_created",
            order_id=str(order.id),
            order_number=order.order_number,
            user_id=user.id,
            amount=float(final_fiat_price),
        )
        return order

    async def transition_order_status(
        self,
        db: AsyncSession,
        order: Order,
        to_status: OrderStatus,
        event_type: str,
        details: Optional[dict] = None,
    ) -> Order:
        """
        Safely transitions order status with audit log in order_events.
        """
        from_status = order.status
        order.status = to_status

        event = OrderEvent(
            order_id=order.id,
            from_status=from_status,
            to_status=to_status,
            event_type=event_type,
            details=details or {},
        )
        db.add(event)
        await db.commit()
        await db.refresh(order)

        logger.info(
            "order_status_transitioned",
            order_id=str(order.id),
            order_number=order.order_number,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            event_type=event_type,
        )
        return order


order_service = OrderService()
