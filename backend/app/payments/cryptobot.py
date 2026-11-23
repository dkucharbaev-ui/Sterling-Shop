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


class CryptoBotProvider(PaymentProvider):
    def __init__(self, token: str = None, network: str = None):
        self.token = token or settings.CRYPTOBOT_API_TOKEN
        self.network = network or settings.CRYPTOBOT_NETWORK
        self.base_url = (
            "https://testnet-pay.crypt.bot/api"
            if self.network == "testnet"
            else "https://pay.crypt.bot/api"
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json",
        }

    async def create_invoice(
        self,
        order_id: str,
        order_number: int,
        amount: Decimal,
        currency: str,
        description: str,
    ) -> PaymentInvoiceResult:
        """
        Calls Crypto Pay API createInvoice endpoint.
        """
        payload = {
            "currency_type": "fiat" if currency.upper() in ["RUB", "USD", "EUR"] else "crypto",
            "fiat": currency.upper() if currency.upper() in ["RUB", "USD", "EUR"] else None,
            "asset": currency.upper() if currency.upper() not in ["RUB", "USD", "EUR"] else None,
            "amount": str(amount),
            "description": description[:1024],
            "payload": str(order_id),
            "expires_in": 900,  # 15 minutes
        }
        # Filter None values
        payload = {k: v for k, v in payload.items() if v is not None}

        # For test environments without real token, return simulated mock URL
        if not self.token or self.token.startswith("1234:AAChange"):
            mock_id = f"cb_{order_number}"
            return PaymentInvoiceResult(
                invoice_id=mock_id,
                payment_url=f"https://t.me/CryptoBot?start={mock_id}",
                amount=amount,
                currency=currency,
                raw_response={"mock": True},
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/createInvoice",
                json=payload,
                headers=self._get_headers(),
            )
            data = resp.json()

            if not data.get("ok"):
                error_msg = data.get("error", {}).get("name", "Unknown CryptoBot error")
                logger.error("cryptobot_create_invoice_failed", error=error_msg, payload=payload)
                raise ValueError(f"CryptoBot error: {error_msg}")

            result = data["result"]
            invoice_id = str(result["invoice_id"])
            payment_url = result.get("mini_app_invoice_url") or result.get("bot_invoice_url") or result.get("pay_url")

            return PaymentInvoiceResult(
                invoice_id=invoice_id,
                payment_url=payment_url,
                amount=Decimal(str(result["amount"])),
                currency=currency,
                raw_response=result,
            )

    async def verify_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
    ) -> WebhookVerificationResult:
        """
        Validates crypto-pay-api-signature header against raw body bytes using HMAC-SHA256.
        Formula:
        secret = SHA256(API_TOKEN)
        HMAC-SHA256(secret, raw_body) == crypto-pay-api-signature
        """
        received_signature = (
            headers.get("crypto-pay-api-signature")
            or headers.get("Crypto-Pay-Api-Signature")
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
                error_message="Missing crypto-pay-api-signature header",
            )

        # 1. secret = SHA256(API_TOKEN)
        secret = hashlib.sha256(self.token.encode("utf-8")).digest()

        # 2. computed_hmac = HMAC-SHA256(secret, raw_body)
        computed_signature = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()

        # 3. Constant-time comparison
        if not hmac.compare_digest(computed_signature, received_signature):
            logger.warning("cryptobot_signature_mismatch", received=received_signature)
            return WebhookVerificationResult(
                is_valid=False,
                order_id="",
                provider_tx_id="",
                status="FAILED",
                paid_amount=Decimal("0"),
                paid_currency="",
                raw_payload={},
                error_message="Invalid webhook signature",
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

        # Structure: {"update_type": "invoice_paid", "payload": { "invoice_id": ..., "payload": "<order_id>", ...}}
        update_type = payload_data.get("update_type")
        invoice = payload_data.get("payload", {})
        order_id = invoice.get("payload", "")
        invoice_id = str(invoice.get("invoice_id", ""))
        amount = Decimal(str(invoice.get("amount", "0")))
        currency = invoice.get("asset") or invoice.get("fiat", "RUB")

        is_paid = update_type == "invoice_paid" or invoice.get("status") == "paid"

        return WebhookVerificationResult(
            is_valid=True,
            order_id=order_id,
            provider_tx_id=invoice_id,
            status="PAID" if is_paid else invoice.get("status", "ACTIVE"),
            paid_amount=amount,
            paid_currency=currency,
            raw_payload=payload_data,
        )

    async def get_invoice_status(self, invoice_id: str) -> PaymentStatusResult:
        """
        Re-verifies payment status with Crypto Pay API to prevent replay / forged status attacks.
        """
        if not self.token or self.token.startswith("1234:AAChange"):
            return PaymentStatusResult(
                invoice_id=invoice_id,
                status="paid",
                is_paid=True,
                paid_amount=Decimal("100.00"),
                currency="RUB",
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/getInvoices",
                params={"invoice_ids": invoice_id},
                headers=self._get_headers(),
            )
            data = resp.json()
            if not data.get("ok") or not data.get("result", {}).get("items"):
                raise ValueError(f"Could not verify invoice {invoice_id} with CryptoBot")

            invoice = data["result"]["items"][0]
            status_val = invoice.get("status", "")
            return PaymentStatusResult(
                invoice_id=invoice_id,
                status=status_val,
                is_paid=(status_val == "paid"),
                paid_amount=Decimal(str(invoice.get("amount", "0"))),
                currency=invoice.get("asset") or invoice.get("fiat", "RUB"),
                raw_response=invoice,
            )
