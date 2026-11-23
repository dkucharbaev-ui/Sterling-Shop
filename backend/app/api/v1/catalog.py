from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.catalog import Category, Product
from app.schemas.catalog import CategoryResponse, ProductResponse, StarsCalculateRequest, StarsCalculateResponse
from app.schemas.order import RecipientValidateRequest, RecipientValidateResponse
from app.services.pricing import pricing_service
from app.services.recipient_check import recipient_check_service

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("", response_model=List[CategoryResponse])
async def get_catalog(db: AsyncSession = Depends(get_db)):
    """
    Returns active product categories and their products with estimated RUB prices.
    """
    query = (
        select(Category)
        .options(selectinload(Category.products))
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order.asc())
    )
    categories = (await db.execute(query)).scalars().all()

    result: List[CategoryResponse] = []
    for cat in categories:
        active_products: List[ProductResponse] = []
        for prod in cat.products:
            if not prod.is_active:
                continue

            # Calculate estimated RUB price for display
            _, est_price = pricing_service.calculate_price(
                base_price_ton=Decimal(str(prod.base_price_ton)),
                quantity=prod.default_quantity,
                margin_percent=Decimal(str(cat.margin_percent)),
                target_currency="RUB",
            )

            p_resp = ProductResponse(
                id=prod.id,
                sku=prod.sku,
                name=prod.name,
                description=prod.description,
                product_type=prod.product_type,
                base_price_ton=Decimal(str(prod.base_price_ton)),
                min_quantity=prod.min_quantity,
                max_quantity=prod.max_quantity,
                default_quantity=prod.default_quantity,
                is_active=prod.is_active,
                sort_order=prod.sort_order,
                metadata_json=prod.metadata_json,
                estimated_price_rub=est_price,
            )
            active_products.append(p_resp)

        cat_resp = CategoryResponse(
            id=cat.id,
            slug=cat.slug,
            name=cat.name,
            description=cat.description,
            icon=cat.icon,
            margin_percent=Decimal(str(cat.margin_percent)),
            is_active=cat.is_active,
            sort_order=cat.sort_order,
            products=active_products,
        )
        result.append(cat_resp)

    return result


@router.post("/stars/calculate", response_model=StarsCalculateResponse)
async def calculate_stars_price(
    payload: StarsCalculateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates live price for any arbitrary number of Stars.
    Formula: Base TON (0.0135 TON / Star) * Quantity * TON_Rate * (1 + Margin%).
    """
    # Fetch stars category margin
    cat_query = select(Category).where(Category.slug == "stars")
    cat = (await db.execute(cat_query)).scalar_one_or_none()
    margin = Decimal(str(cat.margin_percent)) if cat else Decimal("15.00")

    # Fragment base procurement cost per 1 Star is ~0.0135 TON
    base_ton_per_star = Decimal("0.0135")

    ton_rate, final_price = pricing_service.calculate_price(
        base_price_ton=base_ton_per_star,
        quantity=payload.quantity,
        margin_percent=margin,
        target_currency=payload.currency,
    )

    price_per_star = (final_price / Decimal(str(payload.quantity))).quantize(Decimal("0.01"))

    return StarsCalculateResponse(
        quantity=payload.quantity,
        price=final_price,
        currency=payload.currency.upper(),
        price_per_star=price_per_star,
        ton_rate_applied=ton_rate,
    )


@router.post("/recipient/validate", response_model=RecipientValidateResponse)
async def validate_recipient(
    payload: RecipientValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validates recipient @username and checks for active Telegram Premium subscription.
    """
    is_premium = False
    if payload.product_id:
        prod = (await db.execute(select(Product).where(Product.id == payload.product_id))).scalar_one_or_none()
        if prod and "PREMIUM" in prod.product_type:
            is_premium = True

    result = await recipient_check_service.validate_recipient(
        raw_username=payload.username,
        is_premium_product=is_premium,
    )
    return RecipientValidateResponse(
        is_valid=result.is_valid,
        clean_username=result.clean_username,
        has_active_premium=result.has_active_premium,
        error_message=result.error_message,
    )
