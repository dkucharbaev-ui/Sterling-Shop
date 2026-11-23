import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.order import OrderStatus, PaymentProviderType


class CreateOrderRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=1000000)
    recipient_username: str = Field(..., min_length=3, max_length=64)
    payment_provider: PaymentProviderType
    currency: str = Field(default="RUB")
    is_gift: bool = False


class OrderEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: Optional[OrderStatus] = None
    to_status: OrderStatus
    event_type: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: int
    user_id: int
    product_id: uuid.UUID
    quantity: int
    recipient_username: str
    is_gift: bool
    status: OrderStatus
    payment_provider: PaymentProviderType
    payment_invoice_id: Optional[str] = None
    payment_url: Optional[str] = None
    fiat_amount: Decimal
    fiat_currency: str
    crypto_amount: Optional[Decimal] = None
    crypto_currency: Optional[str] = None
    ton_rate_applied: Decimal
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    events: List[OrderEventResponse] = []


class RecipientValidateRequest(BaseModel):
    username: str
    product_id: Optional[uuid.UUID] = None


class RecipientValidateResponse(BaseModel):
    is_valid: bool
    clean_username: str
    has_active_premium: bool = False
    error_message: Optional[str] = None
