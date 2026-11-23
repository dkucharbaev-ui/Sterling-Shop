import uuid
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.fulfillment.mock import MockFulfillmentProvider
from app.fulfillment.service import FulfillmentService
from app.models.catalog import Category, Product
from app.models.order import Order, OrderStatus, PaymentProviderType
from app.models.user import User
from app.services.pricing import CircuitBreakerException, PricingService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_circuit_breaker_volatility_detection():
    service = PricingService()

    base_rate = Decimal("500.00")
    # Small jump: 5% (safe)
    small_jump = Decimal("525.00")
    assert service.check_volatility(small_jump, base_rate, max_allowed_percent=10.0) is True

    # Big jump: 15% (dangerous volatility -> circuit breaker triggered!)
    big_jump = Decimal("575.00")
    assert service.check_volatility(big_jump, base_rate, max_allowed_percent=10.0) is False

    # Attempting to calculate price with extreme volatility must raise CircuitBreakerException
    with pytest.raises(CircuitBreakerException):
        service.calculate_price(
            base_price_ton=Decimal("1.0"),
            quantity=10,
            margin_percent=Decimal("15.0"),
            target_currency="RUB",
            override_rate=big_jump,
            reference_rate=base_rate,
        )


@pytest.mark.asyncio
async def test_fulfillment_successful_lifecycle():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        user = User(id=111222, first_name="FulfillUser")
        db.add(user)
        cat = Category(id=uuid.uuid4(), slug="stars", name="Stars", margin_percent=15.0, is_active=True)
        db.add(cat)
        prod = Product(
            id=uuid.uuid4(),
            category_id=cat.id,
            sku="stars-prod-100",
            name="100 Stars",
            product_type="STARS_FIXED",
            base_price_ton=1.35,
            default_quantity=100,
            is_active=True,
        )
        db.add(prod)
        await db.commit()

        from datetime import datetime, timedelta, timezone

        order = Order(
            id=uuid.uuid4(),
            order_number=200100,
            user_id=user.id,
            product_id=prod.id,
            quantity=100,
            recipient_username="happy_customer",
            status=OrderStatus.PAID,
            payment_provider=PaymentProviderType.CRYPTOBOT,
            fiat_amount=Decimal("1000.00"),
            fiat_currency="RUB",
            ton_rate_applied=Decimal("500.00"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(order)
        await db.commit()

        # Run fulfillment with mock provider
        mock_provider = MockFulfillmentProvider(should_fail=False)
        service = FulfillmentService(provider=mock_provider)

        success = await service.execute_order_fulfillment(db=db, order=order)
        assert success is True

        await db.refresh(order)
        assert order.status == OrderStatus.COMPLETED
        assert order.fulfillment_tx_hash is not None
        assert "mock_tx_stars" in order.fulfillment_tx_hash


@pytest.mark.asyncio
async def test_fulfillment_failure_switches_to_refund_pending():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        user = User(id=333444, first_name="FailUser")
        db.add(user)
        cat = Category(id=uuid.uuid4(), slug="stars", name="Stars", margin_percent=15.0, is_active=True)
        db.add(cat)
        prod = Product(
            id=uuid.uuid4(),
            category_id=cat.id,
            sku="stars-prod-500",
            name="500 Stars",
            product_type="STARS_FIXED",
            base_price_ton=6.75,
            default_quantity=500,
            is_active=True,
        )
        db.add(prod)
        await db.commit()

        from datetime import datetime, timedelta, timezone

        order = Order(
            id=uuid.uuid4(),
            order_number=200200,
            user_id=user.id,
            product_id=prod.id,
            quantity=500,
            recipient_username="unlucky_customer",
            status=OrderStatus.PAID,
            payment_provider=PaymentProviderType.LAVAPAY,
            fiat_amount=Decimal("4500.00"),
            fiat_currency="RUB",
            ton_rate_applied=Decimal("500.00"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(order)
        await db.commit()

        # Run fulfillment with failing mock provider
        failing_provider = MockFulfillmentProvider(should_fail=True)
        service = FulfillmentService(provider=failing_provider)

        success = await service.execute_order_fulfillment(db=db, order=order)
        assert success is False

        await db.refresh(order)
        # MUST transition to REFUND_PENDING
        assert order.status == OrderStatus.REFUND_PENDING
        assert order.fulfillment_error is not None
