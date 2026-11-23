import hashlib
import hmac
import json
from decimal import Decimal
from typing import Dict
import httpx

from app.config import get_settings
from app.core.logger import logger
from app.payments.base import PaymentInvoiceResult, PaymentProvider, PaymentStatusResult, WebhookVerificationResult

settings = get_settings()


class LavaPayProvider(PaymentProvider):
    def __init__(self, shop_id: str = None, secret_key: str = None):
        self.shop_id = shop_id or settings.LAVAPAY_SHOP_ID
        self.secret_key = secret_key or settings.LAVAPAY_SECRET_KEY
        self.base_url = "https://api.lava.ru/business"

    async def create_invoice(
        self,
        order_id: str,
        order_number: int,
        amount: Decimal,
        currency: str,
        description: str,
    ) -> PaymentInvoiceResult:
        """
        Creates an invoice using Lava.ru Business API.
        """
        if not self.shop_id or self.shop_id.startswith("your-shop"):
            mock_id = f"lava_{order_number}"
            return PaymentInvoiceResult(
                invoice_id=mock_id,
                payment_url=f"https://pay.lava.ru/invoice/{mock_id}",
                amount=amount,
                currency=currency,
                raw_response={"mock": True},
            )

        payload = {
            "sum": float(amount),
            "orderId": str(order_id),
            "shopId": self.shop_id,
            "comment": description[:255],
            "expire": 300,
        }
        body_str = json.dumps(payload, separators=(',', ':'))
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            body_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Signature": signature,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/invoice/create",
                data=body_str,
                headers=headers,
            )
            data = resp.json()

            if resp.status_code != 200 or not data.get("data"):
                logger.error("lavapay_create_invoice_failed", status=resp.status_code, data=data)
                err = data.get("error") or "Ошибка создания счета Lava"
                raise ValueError(f"Lava Pay error: {err}")

            inv_data = data["data"]
            invoice_id = str(inv_data.get("id"))
            url = inv_data.get("url")

            return PaymentInvoiceResult(
                invoice_id=invoice_id,
                payment_url=url,
                amount=amount,
                currency=currency,
                raw_response=inv_data,
            )

    async def verify_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookVerificationResult:
        received_signature = (
            headers.get("signature")
            or headers.get("Signature")
            or headers.get("authorization")
            or ""
        )

        if not received_signature:
            return WebhookVerificationResult(
                is_valid=False,
                order_id="",
                provider_tx_id="",
                status="FAILED",
                paid_amount=Decimal("0"),
                paid_currency="",
                raw_payload={},
                error_message="Missing Signature header",
            )

        computed_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed_signature, received_signature):
            logger.warning("lavapay_signature_mismatch", received=received_signature)
            return WebhookVerificationResult(
                is_valid=False,
                order_id="",
                provider_tx_id="",
                status="FAILED",
                paid_amount=Decimal("0"),
                paid_currency="",
                raw_payload={},
                error_message="Invalid Lava Pay signature",
            )

        try:
            payload_data = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            return WebhookVerificationResult(
                is_valid=False,
                order_id="",
                provider_tx_id="",
                status="FAILED",
                paid_amount=Decimal("0"),
                paid_currency="",
                raw_payload={},
                error_message=f"Invalid JSON: {e}",
            )

        order_id = payload_data.get("order_id") or payload_data.get("orderId", "")
        invoice_id = str(payload_data.get("invoice_id") or payload_data.get("invoiceId", "") or payload_data.get("id", ""))
        amount_val = Decimal(str(payload_data.get("amount", payload_data.get("sum", "0"))))
        status_val = str(payload_data.get("status", "")).lower()
        is_paid = status_val in ["success", "paid", "1"]

        return WebhookVerificationResult(
            is_valid=True,
            order_id=order_id,
            provider_tx_id=invoice_id,
            status="PAID" if is_paid else status_val.upper(),
            paid_amount=amount_val,
            paid_currency="RUB",
            raw_payload=payload_data,
        )

    async def get_invoice_status(self, invoice_id: str) -> PaymentStatusResult:
        if not self.shop_id or self.shop_id.startswith("your-shop"):
            return PaymentStatusResult(
                invoice_id=invoice_id,
                status="success",
                is_paid=True,
                paid_amount=Decimal("100.00"),
                currency="RUB",
            )

        payload = {
            "shopId": self.shop_id,
            "invoiceId": invoice_id,
        }
        body_str = json.dumps(payload, separators=(',', ':'))
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            body_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Signature": signature,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/invoice/status",
                data=body_str,
                headers=headers,
            )
            data = resp.json()
            inv_data = data.get("data") or {}
            status_val = str(inv_data.get("status", "")).lower()
            is_paid = status_val in ["success", "paid"]
            return PaymentStatusResult(
                invoice_id=invoice_id,
                status=status_val,
                is_paid=is_paid,
                paid_amount=Decimal(str(inv_data.get("amount", "0"))),
                currency="RUB",
                raw_response=inv_data,
            )
