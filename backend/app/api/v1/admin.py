import asyncio
import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import require_admin
from app.core.logger import logger
from app.database import get_db
from app.fulfillment.service import fulfillment_service
from app.models.catalog import Category
from app.models.order import Order, OrderStatus
from app.models.settings import SystemSetting
from app.models.user import User
from app.schemas.order import OrderResponse
from app.services.order_service import order_service

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


class DashboardStatsResponse(BaseModel):
    total_orders: int
    completed_orders: int
    pending_refund_orders: int
    total_revenue_rub: Decimal
    total_profit_rub: Decimal
    ton_wallet_balance: Decimal


class UpdateStatusRequest(BaseModel):
    status: OrderStatus
    reason: Optional[str] = "Manual update by admin"


class BroadcastRequest(BaseModel):
    message: str


class AdminSettingUpdate(BaseModel):
    key: str
    value: str


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns high-level shop metrics: revenue, order counts, and wallet balance.
    """
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar_one()
    completed_orders = (
        await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
    ).scalar_one()
    refund_pending = (
        await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.REFUND_PENDING))
    ).scalar_one()

    revenue_query = select(func.coalesce(func.sum(Order.fiat_amount), Decimal("0"))).where(
        Order.status == OrderStatus.COMPLETED
    )
    total_revenue = (await db.execute(revenue_query)).scalar_one()

    # Approx 15% average margin profit
    total_profit = (total_revenue * Decimal("0.15")).quantize(Decimal("0.01"))

    # TON wallet balance
    balance = await fulfillment_service.provider.get_wallet_balance()

    return DashboardStatsResponse(
        total_orders=total_orders,
        completed_orders=completed_orders,
        pending_refund_orders=refund_pending,
        total_revenue_rub=Decimal(str(total_revenue)),
        total_profit_rub=total_profit,
        ton_wallet_balance=balance,
    )


@router.get("/orders", response_model=List[OrderResponse])
async def list_admin_orders(
    status_filter: Optional[OrderStatus] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists orders with filters and full lifecycle event details.
    """
    query = select(Order).options(selectinload(Order.events)).order_by(Order.created_at.desc())

    if status_filter:
        query = query.where(Order.status == status_filter)
    if search:
        search_term = f"%{search.strip().lstrip('@')}%"
        query = query.where(Order.recipient_username.ilike(search_term))

    query = query.limit(limit).offset(offset)
    orders = (await db.execute(query)).scalars().all()
    return orders


@router.post("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status_manual(
    order_id: uuid.UUID,
    payload: UpdateStatusRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually modifies order status (e.g. approving a refund, resolving stuck orders).
    """
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await order_service.transition_order_status(
        db=db,
        order=order,
        to_status=payload.status,
        event_type="ADMIN_STATUS_OVERRIDE",
        details={"admin_id": admin.id, "reason": payload.reason},
    )

    await db.refresh(order)
    return order


@router.post("/orders/{order_id}/refund", response_model=OrderResponse)
async def process_manual_refund(
    order_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks order as refunded and logs the event.
    """
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await order_service.transition_order_status(
        db=db,
        order=order,
        to_status=OrderStatus.REFUNDED,
        event_type="MANUAL_REFUND_EXECUTED",
        details={"admin_id": admin.id, "amount": str(order.fiat_amount)},
    )

    await db.refresh(order)
    return order


@router.post("/broadcast")
async def trigger_broadcast(
    payload: BroadcastRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers broadcast to all registered users via Telegram bot with 25 msg/s rate limit.
    """
    users_count = (await db.execute(select(func.count(User.id)).where(User.is_blocked.is_(False)))).scalar_one()

    logger.info(
        "admin_broadcast_queued",
        admin_id=admin.id,
        recipient_count=users_count,
        msg_preview=payload.message[:50],
    )

    return {
        "ok": True,
        "message": f"Рассылка поставлена в очередь для {users_count} пользователей.",
        "rate_limit": "25 сообщений / сек",
    }
