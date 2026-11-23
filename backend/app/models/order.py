import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAID = "PAID"
    FULFILLING = "FULFILLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class PaymentProviderType(str, enum.Enum):
    CRYPTOBOT = "CRYPTOBOT"
    LAVAPAY = "LAVAPAY"
    MOCK = "MOCK"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Human-readable incremental order number
    order_number: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, autoincrement=True)
    
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recipient_username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_gift: Mapped[bool] = mapped_column(default=False, nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False),
        default=OrderStatus.CREATED,
        index=True,
        nullable=False,
    )

    payment_provider: Mapped[PaymentProviderType] = mapped_column(
        Enum(PaymentProviderType, native_enum=False),
        nullable=False,
    )
    payment_invoice_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    payment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stored in Decimal/Numeric(14, 2)
    fiat_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    fiat_currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)
    crypto_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    crypto_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Applied TON exchange rate at checkout time
    ton_rate_applied: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)

    # Fulfillment tracking
    fulfillment_tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    fulfillment_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fulfillment_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="selectin")
    events: Mapped[list["OrderEvent"]] = relationship(
        "OrderEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    from_status: Mapped[Optional[OrderStatus]] = mapped_column(Enum(OrderStatus, native_enum=False), nullable=True)
    to_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, native_enum=False), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="events")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[PaymentProviderType] = mapped_column(Enum(PaymentProviderType, native_enum=False), nullable=False)
    provider_tx_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
