import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logger import logger
from app.fulfillment.base import FulfillmentProvider, FulfillmentResult
from app.fulfillment.fragment.client import FragmentProvider
from app.fulfillment.mock import MockFulfillmentProvider
from app.models.catalog import Product
from app.models.order import Order, OrderStatus
from app.services.order_service import order_service

settings = get_settings()


def get_fulfillment_provider() -> FulfillmentProvider:
    if settings.DRY_RUN_FULFILLMENT:
        return MockFulfillmentProvider()
    return FragmentProvider()


class FulfillmentService:
    def __init__(self, provider: Optional[FulfillmentProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> FulfillmentProvider:
        return self._provider or get_fulfillment_provider()

    async def execute_order_fulfillment(
        self,
        db: AsyncSession,
        order: Order,
    ) -> bool:
        """
        Executes order fulfillment lifecycle:
        PAID -> FULFILLING -> COMPLETED (or REFUND_PENDING on failure)
        """
        if order.status != OrderStatus.PAID:
            logger.warning("order_not_in_paid_status", order_id=str(order.id), status=order.status.value)
            return False

        # Transition to FULFILLING
        await order_service.transition_order_status(
            db=db,
            order=order,
            to_status=OrderStatus.FULFILLING,
            event_type="FULFILLMENT_STARTED",
        )

        prod_query = select(Product).where(Product.id == order.product_id)
        product = (await db.execute(prod_query)).scalar_one()

        result: FulfillmentResult
        if "PREMIUM" in product.product_type:
            months = product.default_quantity or 3
            result = await self.provider.fulfill_premium(
                recipient_username=order.recipient_username,
                months=months,
                order_number=order.order_number,
            )
        else:
            result = await self.provider.fulfill_stars(
                recipient_username=order.recipient_username,
                quantity=order.quantity,
                order_number=order.order_number,
            )

        if result.is_success:
            order.fulfillment_tx_hash = result.tx_hash
            await order_service.transition_order_status(
                db=db,
                order=order,
                to_status=OrderStatus.COMPLETED,
                event_type="FULFILLMENT_COMPLETED",
                details={"tx_hash": result.tx_hash, "details": result.raw_details},
            )
            logger.info("order_fulfilled_successfully", order_number=order.order_number, tx_hash=result.tx_hash)
            return True
        else:
            order.fulfillment_error = result.error_message
            # Switch to REFUND_PENDING as required by user specification
            await order_service.transition_order_status(
                db=db,
                order=order,
                to_status=OrderStatus.REFUND_PENDING,
                event_type="FULFILLMENT_FAILED_NEEDS_REFUND",
                details={"error": result.error_message},
            )
            logger.error("order_fulfillment_failed_refund_pending", order_number=order.order_number, error=result.error_message)
            return False


fulfillment_service = FulfillmentService()
