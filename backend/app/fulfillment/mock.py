import uuid
from decimal import Decimal
from typing import Dict
from app.core.logger import logger
from app.fulfillment.base import FulfillmentProvider, FulfillmentResult


class MockFulfillmentProvider(FulfillmentProvider):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.balance = Decimal("150.00")

    async def fulfill_stars(
        self,
        recipient_username: str,
        quantity: int,
        order_number: int,
    ) -> FulfillmentResult:
        if self.should_fail:
            return FulfillmentResult(
                is_success=False,
                error_message="Simulated Fragment fulfillment failure",
            )
        tx_hash = f"mock_tx_stars_{uuid.uuid4().hex[:16]}"
        logger.info(
            "mock_stars_fulfilled",
            recipient=recipient_username,
            quantity=quantity,
            tx_hash=tx_hash,
        )
        return FulfillmentResult(
            is_success=True,
            tx_hash=tx_hash,
            raw_details={"mock": True, "stars": quantity},
        )

    async def fulfill_premium(
        self,
        recipient_username: str,
        months: int,
        order_number: int,
    ) -> FulfillmentResult:
        if self.should_fail:
            return FulfillmentResult(
                is_success=False,
                error_message="Simulated Fragment fulfillment failure",
            )
        tx_hash = f"mock_tx_premium_{uuid.uuid4().hex[:16]}"
        logger.info(
            "mock_premium_fulfilled",
            recipient=recipient_username,
            months=months,
            tx_hash=tx_hash,
        )
        return FulfillmentResult(
            is_success=True,
            tx_hash=tx_hash,
            raw_details={"mock": True, "months": months},
        )

    async def get_wallet_balance(self) -> Decimal:
        return self.balance
