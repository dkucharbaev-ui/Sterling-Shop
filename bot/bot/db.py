"""Lightweight DB layer for the bot — works directly with SQLite via the backend models."""
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.database import Base
from app.models.catalog import Category, Product
from app.models.order import Order, OrderStatus, PaymentProviderType
from app.models.user import User
from app.models.settings import CurrencyRate, SystemSetting

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "psycho_stars.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed catalog if empty
    async with async_session() as db:
        cats = (await db.execute(select(Category))).scalars().all()
        if cats:
            return
        # Stars
        stars = Category(
            id=uuid.uuid4(), slug="stars", name="⭐ Telegram Stars",
            description="Звёзды Telegram для каналов, ботов и реакций", icon="star",
            margin_percent=15.00, is_active=True, sort_order=1,
        )
        db.add(stars)
        await db.flush()
        db.add(Product(
            id=uuid.uuid4(), category_id=stars.id, sku="stars-custom",
            name="Telegram Stars", description="От 50 до 100 000 звёзд (1.65₽ / шт.)",
            product_type="STARS_CUSTOM", base_price_ton=Decimal("0.0135"),
            min_quantity=50, max_quantity=100000, default_quantity=100,
            is_active=True, sort_order=1,
        ))
        # Premium
        prem = Category(
            id=uuid.uuid4(), slug="premium", name="💎 Telegram Premium",
            description="Подписка Telegram Premium", icon="shield",
            margin_percent=18.00, is_active=True, sort_order=2,
        )
        db.add(prem)
        await db.flush()
        for sku, name, ton, months, idx in [
            ("premium-3m", "Premium 3 мес.", Decimal("2.20"), 3, 1),
            ("premium-6m", "Premium 6 мес.", Decimal("3.90"), 6, 2),
            ("premium-12m", "Premium 12 мес.", Decimal("6.90"), 12, 3),
        ]:
            db.add(Product(
                id=uuid.uuid4(), category_id=prem.id, sku=sku, name=name,
                description=f"Подписка на {months} мес.",
                product_type="PREMIUM_MONTHS", base_price_ton=ton,
                default_quantity=months, is_active=True, sort_order=idx,
            ))
        await db.commit()
        print("✅ Каталог создан и заполнен")


async def get_or_create_user(db: AsyncSession, tg_user) -> User:
    user = (await db.execute(select(User).where(User.id == tg_user.id))).scalar_one_or_none()
    if not user:
        user = User(
            id=tg_user.id,
            first_name=tg_user.first_name or "User",
            last_name=tg_user.last_name,
            username=tg_user.username,
            is_premium=getattr(tg_user, "is_premium", False) or False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_categories(db: AsyncSession):
    result = await db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
    )
    return result.scalars().all()


async def get_products_by_category(db: AsyncSession, slug: str):
    result = await db.execute(
        select(Product)
        .join(Category)
        .options(selectinload(Product.category))
        .where(Category.slug == slug, Product.is_active.is_(True))
        .order_by(Product.sort_order)
    )
    return result.scalars().all()


async def get_product_by_id(db: AsyncSession, product_id: str) -> Product | None:
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        return None
    result = await db.execute(
        select(Product).options(selectinload(Product.category))
        .where(Product.id == pid)
    )
    return result.scalar_one_or_none()


async def get_user_orders(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    return result.scalars().all()


async def get_order_by_number(db: AsyncSession, order_number: int, user_id: int):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.order_number == order_number, Order.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_order_by_id(db: AsyncSession, order_id: str) -> Order | None:
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        return None
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.id == oid)
    )
    return result.scalar_one_or_none()


async def get_order_by_number_any_user(db: AsyncSession, order_number: int) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.order_number == order_number)
    )
    return result.scalar_one_or_none()
