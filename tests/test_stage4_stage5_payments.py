import hashlib
import hmac
import json
import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.catalog import Category, Product
from app.models.order import Order, OrderStatus, PaymentProviderType, PaymentTransaction
from app.models.user import User
from app.payments.cryptobot import CryptoBotProvider
from app.payments.lavapay import LavaPayProvider
from app.payments.service import payment_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


def compute_cryptobot_sig(token: str, body: bytes) -> str:
    secret = hashlib.sha256(token.encode("utf-8")).digest()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def compute_lavapay_sig(secret_key: str, body: bytes) -> str:
    return hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_cryptobot_signature_verification():
    token = "test_cb_token_123"
    provider = CryptoBotProvider(token=token)

    payload = {
        "update_type": "invoice_paid",
        "payload": {
            "invoice_id": 998877,
            "status": "paid",
            "amount": "500.00",
            "asset": "USDT",
            "payload": str(uuid.uuid4()),
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_cryptobot_sig(token, raw_body)

    # Valid
    res = await provider.verify_webhook({"crypto-pay-api-signature": sig}, raw_body)
    assert res.is_valid is True
    assert res.provider_tx_id == "998877"
    assert res.status == "PAID"
    assert res.paid_amount == Decimal("500.00")

    # Invalid signature
    res_bad = await provider.verify_webhook({"crypto-pay-api-signature": "bad_sig"}, raw_body)
    assert res_bad.is_valid is False


@pytest.mark.asyncio
async def test_lavapay_signature_verification():
    secret_key = "test_lava_secret_key"
    provider = LavaPayProvider(shop_id="shop_123", secret_key=secret_key)

    order_uuid = str(uuid.uuid4())
    payload = {
        "order_id": order_uuid,
        "invoice_id": "lava_inv_5544",
        "amount": 750.50,
        "status": "success",
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_lavapay_sig(secret_key, raw_body)

    res = await provider.verify_webhook({"Signature": sig}, raw_body)
    assert res.is_valid is True
    assert res.order_id == order_uuid
    assert res.provider_tx_id == "lava_inv_5544"
    assert res.status == "PAID"
    assert res.paid_amount == Decimal("750.50")


@pytest.mark.asyncio
async def test_payment_webhook_idempotency_and_order_transition():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    settings.CRYPTOBOT_API_TOKEN = "crypto_bot_test_token"

    async with async_session() as db:
        user = User(id=889900, first_name="Payer")
        db.add(user)
        cat = Category(id=uuid.uuid4(), slug="stars", name="Stars", margin_percent=10.0, is_active=True)
        db.add(cat)
        prod = Product(
            id=uuid.uuid4(),
            category_id=cat.id,
            sku="stars-pack-100",
            name="100 Stars",
            product_type="STARS_FIXED",
            base_price_ton=1.35,
            default_quantity=100,
            is_active=True,
        )
        db.add(prod)
        await db.commit()

        # Create Order
        order_id = uuid.uuid4()
        from datetime import datetime, timedelta, timezone

        order = Order(
            id=order_id,
            order_number=100500,
            user_id=user.id,
            product_id=prod.id,
            quantity=100,
            recipient_username="test_recipient",
            status=OrderStatus.AWAITING_PAYMENT,
            payment_provider=PaymentProviderType.CRYPTOBOT,
            fiat_amount=Decimal("1000.00"),
            fiat_currency="RUB",
            ton_rate_applied=Decimal("500.00"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(order)
        await db.commit()

        # Build webhook payload
        payload = {
            "update_type": "invoice_paid",
            "payload": {
                "invoice_id": "tx_cb_100500",
                "status": "paid",
                "amount": "1000.00",
                "asset": "RUB",
                "payload": str(order_id),
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = compute_cryptobot_sig(settings.CRYPTOBOT_API_TOKEN, raw_body)
        headers = {"crypto-pay-api-signature": sig}

        # 1. First webhook delivery
        success = await payment_service.process_webhook(
            provider_type=PaymentProviderType.CRYPTOBOT,
            headers=headers,
            raw_body=raw_body,
            db=db,
        )
        assert success is True

        # Check order is marked PAID
        await db.refresh(order)
        assert order.status == OrderStatus.PAID

        # Check PaymentTransaction created
        txs = (await db.execute(select(PaymentTransaction).where(PaymentTransaction.order_id == order.id))).scalars().all()
        assert len(txs) == 1
        assert txs[0].provider_tx_id == "tx_cb_100500"

        # 2. Duplicate webhook delivery (idempotency check)
        success_dup = await payment_service.process_webhook(
            provider_type=PaymentProviderType.CRYPTOBOT,
            headers=headers,
            raw_body=raw_body,
            db=db,
        )
        assert success_dup is True

        # Ensure no duplicate transactions added
        txs_after = (await db.execute(select(PaymentTransaction).where(PaymentTransaction.order_id == order.id))).scalars().all()
        assert len(txs_after) == 1
