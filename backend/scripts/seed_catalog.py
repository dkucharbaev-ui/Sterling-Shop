import asyncio
import uuid
from decimal import Decimal
from sqlalchemy import select
from app.database import async_session_maker
from app.models.catalog import Category, Product
from app.models.settings import CurrencyRate, SystemSetting


async def seed():
    async with async_session_maker() as db:
        # 1. System Settings & Rates
        rates = [
            CurrencyRate(pair="TON_RUB", rate=Decimal("520.00"), source="initial"),
            CurrencyRate(pair="TON_USDT", rate=Decimal("5.50"), source="initial"),
        ]
        for r in rates:
            existing = (await db.execute(select(CurrencyRate).where(CurrencyRate.pair == r.pair))).scalar_one_or_none()
            if not existing:
                db.add(r)

        # 2. Category: Telegram Stars
        stars_cat = (await db.execute(select(Category).where(Category.slug == "stars"))).scalar_one_or_none()
        if not stars_cat:
            stars_cat = Category(
                id=uuid.uuid4(),
                slug="stars",
                name="Telegram Stars",
                description="Официальные звёзды Telegram для каналов, ботов и реакций",
                icon="star",
                margin_percent=15.00,
                is_active=True,
                sort_order=1,
            )
            db.add(stars_cat)
            await db.flush()

            # Custom Stars product
            db.add(
                Product(
                    id=uuid.uuid4(),
                    category_id=stars_cat.id,
                    sku="stars-custom",
                    name="Telegram Stars (Любое количество)",
                    description="Укажите нужное количество от 50 до 100 000 звёзд",
                    product_type="STARS_CUSTOM",
                    base_price_ton=0.0135,
                    min_quantity=50,
                    max_quantity=100000,
                    default_quantity=100,
                    is_active=True,
                    sort_order=1,
                )
            )

        # 3. Category: Telegram Premium
        premium_cat = (await db.execute(select(Category).where(Category.slug == "premium"))).scalar_one_or_none()
        if not premium_cat:
            premium_cat = Category(
                id=uuid.uuid4(),
                slug="premium",
                name="Telegram Premium",
                description="Подписка Telegram Premium с удвоенными лимитами и возможностями",
                icon="shield",
                margin_percent=18.00,
                is_active=True,
                sort_order=2,
            )
            db.add(premium_cat)
            await db.flush()

            # Premium plans
            plans = [
                ("premium-3m", "Telegram Premium 3 месяца", 2.20, 3, 1),
                ("premium-6m", "Telegram Premium 6 месяцев", 3.90, 6, 2),
                ("premium-12m", "Telegram Premium 12 месяцев (1 год)", 6.90, 12, 3),
            ]
            for sku, name, ton_cost, months, order_idx in plans:
                db.add(
                    Product(
                        id=uuid.uuid4(),
                        category_id=premium_cat.id,
                        sku=sku,
                        name=name,
                        description=f"Подписка Telegram Premium на {months} мес.",
                        product_type="PREMIUM_MONTHS",
                        base_price_ton=ton_cost,
                        default_quantity=months,
                        is_active=True,
                        sort_order=order_idx,
                    )
                )

        await db.commit()
        print("✅ Database successfully seeded with categories and initial products!")


if __name__ == "__main__":
    asyncio.run(seed())
