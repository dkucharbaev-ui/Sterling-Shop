import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.catalog import Category, Product
from app.models.order import OrderStatus, PaymentProviderType
from app.models.user import User
from app.schemas.order import CreateOrderRequest
from app.services.order_service import MAX_UNPAID_ORDERS_PER_USER, order_service
from app.services.pricing import pricing_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_pricing_calculation():
    # Base: 0.0135 TON, Quantity: 1000 Stars, Margin: 15%, TON rate: 500 RUB
    # Raw TON: 13.5 TON
    # Raw Fiat: 13.5 * 500 = 6750 RUB
    # Final Fiat: 6750 * 1.15 = 7762.50 RUB
    rate, final_price = pricing_service.calculate_price(
        base_price_ton=Decimal("0.0135"),
        quantity=1000,
        margin_percent=Decimal("15.00"),
        target_currency="RUB",
        override_rate=Decimal("500.00"),
    )
    assert rate == Decimal("500.00")
    assert final_price == Decimal("7762.50")


@pytest.mark.asyncio
async def test_order_creation_and_lifecycle():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # 1. Create User
        user = User(id=11223344, first_name="Tester", username="tester_tg")
        db.add(user)

        # 2. Create Category
        cat = Category(
            id=uuid.uuid4(),
            slug="stars",
            name="Telegram Stars",
            margin_percent=15.00,
            is_active=True,
            sort_order=1,
        )
        db.add(cat)

        # 3. Create Product
        prod = Product(
            id=uuid.uuid4(),
            category_id=cat.id,
            sku="stars-custom",
            name="Telegram Stars (Any amount)",
            product_type="STARS_CUSTOM",
            base_price_ton=0.0135,
            min_quantity=50,
            max_quantity=100000,
            default_quantity=100,
            is_active=True,
        )
        db.add(prod)
        await db.commit()

        # 4. Create Order
        req = CreateOrderRequest(
            product_id=prod.id,
            quantity=500,
            recipient_username="friend_username",
            payment_provider=PaymentProviderType.CRYPTOBOT,
            currency="RUB",
        )

        order = await order_service.create_order(db=db, user=user, payload=req)
        assert order.status == OrderStatus.CREATED
        assert order.quantity == 500
        assert order.recipient_username == "friend_username"
        assert order.order_number >= 100000

        # Check OrderEvent logged
        assert len(order.events) == 1
        assert order.events[0].to_status == OrderStatus.CREATED
        assert order.events[0].event_type == "ORDER_CREATED"

        # 5. Transition order to AWAITING_PAYMENT
        await order_service.transition_order_status(
            db=db,
            order=order,
            to_status=OrderStatus.AWAITING_PAYMENT,
            event_type="INVOICE_CREATED",
            details={"invoice_id": "inv_123"},
        )
        assert order.status == OrderStatus.AWAITING_PAYMENT
        assert len(order.events) == 2


@pytest.mark.asyncio
async def test_order_anti_spam_limit():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        user = User(id=55667788, first_name="SpamTester", username="spammer")
        db.add(user)
        cat = Category(id=uuid.uuid4(), slug="stars", name="Stars", margin_percent=10.0, is_active=True)
        db.add(cat)
        prod = Product(
            id=uuid.uuid4(),
            category_id=cat.id,
            sku="stars-pack-50",
            name="50 Stars",
            product_type="STARS_FIXED",
            base_price_ton=0.675,
            default_quantity=50,
            is_active=True,
        )
        db.add(prod)
        await db.commit()

        req = CreateOrderRequest(
            product_id=prod.id,
            quantity=50,
            recipient_username="target_user",
            payment_provider=PaymentProviderType.LAVAPAY,
        )

        # Create 3 orders (the maximum allowed)
        for _ in range(MAX_UNPAID_ORDERS_PER_USER):
            await order_service.create_order(db=db, user=user, payload=req)

        # 4th order must be rejected
        with pytest.raises(ValueError, match="активных неоплаченных заказов"):
            await order_service.create_order(db=db, user=user, payload=req)
