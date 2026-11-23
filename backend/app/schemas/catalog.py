import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    description: Optional[str] = None
    product_type: str
    base_price_ton: Decimal
    min_quantity: Optional[int] = 1
    max_quantity: Optional[int] = 100000
    default_quantity: int = 1
    is_active: bool
    sort_order: int
    metadata_json: Optional[Dict[str, Any]] = None
    # Computed estimated price for UI display
    estimated_price_rub: Optional[Decimal] = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    margin_percent: Decimal
    is_active: bool
    sort_order: int
    products: List[ProductResponse] = []


class StarsCalculateRequest(BaseModel):
    quantity: int = Field(..., ge=1, le=1000000, description="Количество звёзд")
    currency: str = Field(default="RUB", description="Валюта расчета (RUB / USDT)")


class StarsCalculateResponse(BaseModel):
    quantity: int
    price: Decimal
    currency: str
    price_per_star: Decimal
    ton_rate_applied: Decimal
