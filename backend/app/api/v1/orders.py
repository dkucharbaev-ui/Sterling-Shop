import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.order import CreateOrderRequest, OrderResponse
from app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new order. User identity is taken strictly from the verified JWT session.
    """
    try:
        order = await order_service.create_order(
            db=db,
            user=current_user,
            payload=payload,
        )
        # Load relationships for response
        order_with_rels = (
            await db.execute(
                select(Order).options(selectinload(Order.events)).where(Order.id == order.id)
            )
        ).scalar_one()
        return order_with_rels
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=List[OrderResponse])
async def get_my_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all orders placed by the currently authenticated user.
    """
    query = (
        select(Order)
        .options(selectinload(Order.events))
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = (await db.execute(query)).scalars().all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches details of a specific order belonging to the current user.
    """
    query = (
        select(Order)
        .options(selectinload(Order.events))
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = (await db.execute(query)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден",
        )
    return order


@router.get("/{order_id}/status")
async def get_order_status_poll(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fast polling endpoint for frontend real-time status updates.
    """
    query = select(Order.status, Order.payment_url, Order.fulfillment_error).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
    )
    res = (await db.execute(query)).one_or_none()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден",
        )
    return {
        "order_id": str(order_id),
        "status": res[0].value,
        "payment_url": res[1],
        "fulfillment_error": res[2],
    }
