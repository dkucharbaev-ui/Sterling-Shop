import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.catalog import Category, Product
from app.models.order import Order, OrderStatus, PaymentProviderType
from app.models.user import User


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_admin_access_control():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    settings.ADMIN_IDS_RAW = "999888"

    async with async_session() as db:
        # Regular user
        regular_user = User(id=111000, first_name="Regular")
        # Admin user
        admin_user = User(id=999888, first_name="Admin")
        db.add_all([regular_user, admin_user])
        await db.commit()

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_token = create_access_token(subject=111000)
        admin_token = create_access_token(subject=999888)

        # 1. Non-admin access should be denied (403)
        res_denied = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {reg_token}"},
        )
        assert res_denied.status_code == 403

        # 2. Admin access should be granted (200)
        res_allowed = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_allowed.status_code == 200
        data = res_allowed.json()
        assert "total_orders" in data
        assert "ton_wallet_balance" in data

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_manual_refund_action():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    settings.ADMIN_IDS_RAW = "777000"

    async with async_session() as db:
        admin_user = User(id=777000, first_name="SuperAdmin")
        db.add(admin_user)
        cat = Category(id=uuid.uuid4(), slug="stars", name="Stars", margin_percent=15.0, is_active=True)
        db.add(cat)
        prod = Product(
            id=uuid.uuid4(),
            category_id=cat.id,
            sku="stars-100",
            name="100 Stars",
            product_type="STARS_FIXED",
            base_price_ton=1.35,
            default_quantity=100,
            is_active=True,
        )
        db.add(prod)

        from datetime import datetime, timedelta, timezone

        order = Order(
            id=uuid.uuid4(),
            order_number=500600,
            user_id=admin_user.id,
            product_id=prod.id,
            quantity=100,
            recipient_username="test_refund_user",
            status=OrderStatus.REFUND_PENDING,
            payment_provider=PaymentProviderType.CRYPTOBOT,
            fiat_amount=Decimal("1500.00"),
            fiat_currency="RUB",
            ton_rate_applied=Decimal("500.00"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(order)
        await db.commit()

        order_id = order.id

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = create_access_token(subject=777000)

        # Trigger manual refund
        res = await client.post(
            f"/api/v1/admin/orders/{order_id}/refund",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        refunded_order = res.json()
        assert refunded_order["status"] == "REFUNDED"

    app.dependency_overrides.clear()
