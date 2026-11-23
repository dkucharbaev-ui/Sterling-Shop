from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel


class PaymentInvoiceResult(BaseModel):
    invoice_id: str
    payment_url: str
    amount: Decimal
    currency: str
    raw_response: Optional[Dict[str, Any]] = None


class WebhookVerificationResult(BaseModel):
    is_valid: bool
    order_id: str
    provider_tx_id: str
    status: str  # PAID, EXPIRED, FAILED
    paid_amount: Decimal
    paid_currency: str
    raw_payload: Dict[str, Any]
    error_message: Optional[str] = None


class PaymentStatusResult(BaseModel):
    invoice_id: str
    status: str
    is_paid: bool
    paid_amount: Decimal
    currency: str
    raw_response: Optional[Dict[str, Any]] = None


class PaymentProvider(ABC):
    @abstractmethod
    async def create_invoice(
        self,
        order_id: str,
        order_number: int,
        amount: Decimal,
        currency: str,
        description: str,
    ) -> PaymentInvoiceResult:
        """Creates an invoice with the payment provider"""
        pass

    @abstractmethod
    async def verify_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookVerificationResult:
        """Verifies cryptographic signature of incoming webhook and extracts payment data"""
        pass

    @abstractmethod
    async def get_invoice_status(
        self,
        invoice_id: str,
    ) -> PaymentStatusResult:
        """Queries provider API to check current status of invoice"""
        pass
