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
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # 1. Проверяем категорию Stars (скрыта по запросу)
        stars = (await db.execute(select(Category).where(Category.slug == "stars"))).scalar_one_or_none()
        if not stars:
            stars = Category(
                id=uuid.uuid4(), slug="stars", name="⭐ Telegram Stars",
                description="Звёзды Telegram для каналов, ботов и реакций", icon="star",
                margin_percent=15.00, is_active=False, sort_order=1,
            )
            db.add(stars)
            await db.flush()
            db.add(Product(
                id=uuid.uuid4(), category_id=stars.id, sku="stars-custom",
                name="Telegram Stars", description="От 50 до 100 000 звёзд (1.65₽ / шт.)",
                product_type="STARS_CUSTOM", base_price_ton=Decimal("0.0135"),
                min_quantity=50, max_quantity=100000, default_quantity=100,
                is_active=False, sort_order=1,
            ))

        # 2. Проверяем категорию Premium (скрыта по запросу)
        prem = (await db.execute(select(Category).where(Category.slug == "premium"))).scalar_one_or_none()
        if not prem:
            prem = Category(
                id=uuid.uuid4(), slug="premium", name="💎 Telegram Premium",
                description="Подписка Telegram Premium", icon="shield",
                margin_percent=18.00, is_active=False, sort_order=2,
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
                    default_quantity=months, is_active=False, sort_order=idx,
                ))

        # 3. Проверяем категорию VPN (активна!)
        vpn_cat = (await db.execute(select(Category).where(Category.slug == "vpn"))).scalar_one_or_none()
        if not vpn_cat:
            vpn_cat = Category(
                id=uuid.uuid4(), slug="vpn", name="🛡 VPN подписка",
                description="Скоростной VPN для всех устройств", icon="shield",
                margin_percent=0.00, is_active=True, sort_order=3,
            )
            db.add(vpn_cat)
            await db.flush()

        # Проверяем товары VPN
        vpn_products = [
            ("vpn-1m", "VPN 1 месяц", 199.0, 1, 1),
            ("vpn-3m", "VPN 3 месяца", 499.0, 3, 2),
            ("vpn-6m", "VPN 6 месяцев", 899.0, 6, 3),
            ("vpn-12m", "VPN 12 месяцев (год)", 1499.0, 12, 4),
        ]
        for sku, name, rub, months, idx in vpn_products:
            existing_prod = (await db.execute(select(Product).where(Product.sku == sku))).scalar_one_or_none()
            if not existing_prod:
                db.add(Product(
                    id=uuid.uuid4(),
                    category_id=vpn_cat.id,
                    sku=sku,
                    name=name,
                    description=f"Безлимитный скоростной VPN на {months} мес. Для всех устройств.",
                    product_type="VPN_SUBSCRIPTION",
                    base_price_ton=Decimal("0"),
                    min_quantity=1,
                    max_quantity=1,
                    default_quantity=months,
                    metadata_json={"price_rub": rub, "months": months},
                    is_active=True,
                    sort_order=idx,
                ))

        await db.commit()
        print("✅ База данных инициализирована и каталоги обновлены")


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


async def get_product_by_id(db: AsyncSession, product_id: str | uuid.UUID | None) -> Product | None:
    if not product_id:
        return None

    str_id = str(product_id).strip()

    # 1. Поиск по SKU (например 'vpn-1m', 'stars-custom')
    result = await db.execute(
        select(Product).options(selectinload(Product.category))
        .where(Product.sku == str_id)
    )
    prod = result.scalar_one_or_none()
    if prod:
        return prod

    # 2. Поиск по UUID
    try:
        if isinstance(product_id, uuid.UUID):
            pid = product_id
        else:
            pid = uuid.UUID(str_id)
        result = await db.execute(
            select(Product).options(selectinload(Product.category))
            .where(Product.id == pid)
        )
        prod = result.scalar_one_or_none()
        if prod:
            return prod
    except (ValueError, TypeError, AttributeError):
        pass

    # 3. Fallback: если пришёл старый ID до пересидирования базы, пытаемся найти любой активный VPN-товар
    if "vpn" in str_id.lower():
        result = await db.execute(
            select(Product).options(selectinload(Product.category))
            .where(Product.product_type == "VPN_SUBSCRIPTION", Product.is_active.is_(True))
            .order_by(Product.sort_order)
        )
        return result.scalars().first()

    return None


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


async def get_order_by_id(db: AsyncSession, order_id: str | uuid.UUID | None) -> Order | None:
    if not order_id:
        return None
    try:
        if isinstance(order_id, uuid.UUID):
            oid = order_id
        else:
            oid = uuid.UUID(str(order_id))
    except (ValueError, TypeError, AttributeError):
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
