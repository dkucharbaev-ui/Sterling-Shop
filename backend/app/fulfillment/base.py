from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel


class FulfillmentResult(BaseModel):
    is_success: bool
    tx_hash: Optional[str] = None
    error_message: Optional[str] = None
    raw_details: Optional[Dict[str, Any]] = None


class FulfillmentProvider(ABC):
    @abstractmethod
    async def fulfill_stars(
        self,
        recipient_username: str,
        quantity: int,
        order_number: int,
    ) -> FulfillmentResult:
        """Fulfills Telegram Stars delivery to the recipient"""
        pass

    @abstractmethod
    async def fulfill_premium(
        self,
        recipient_username: str,
        months: int,
        order_number: int,
    ) -> FulfillmentResult:
        """Fulfills Telegram Premium subscription gifting to the recipient"""
        pass

    @abstractmethod
    async def get_wallet_balance(self) -> Decimal:
        """Returns the available balance of the fulfillment TON wallet in TON"""
        pass
