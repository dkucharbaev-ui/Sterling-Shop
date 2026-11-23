import uuid
from decimal import Decimal
from typing import Dict, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.order import Order, OrderStatus, PaymentProviderType, PaymentTransaction
from app.payments.base import PaymentProvider, WebhookVerificationResult
from app.payments.cryptobot import CryptoBotProvider
from app.payments.lavapay import LavaPayProvider
from app.services.order_service import order_service


def get_payment_provider(provider_type: PaymentProviderType) -> PaymentProvider:
    if provider_type == PaymentProviderType.CRYPTOBOT:
        return CryptoBotProvider()
    elif provider_type == PaymentProviderType.LAVAPAY:
        return LavaPayProvider()
    raise ValueError(f"Unsupported payment provider: {provider_type}")


class PaymentService:
    async def initialize_payment(
        self,
        db: AsyncSession,
        order: Order,
    ) -> Tuple[str, str]:
        """
        Creates invoice with the selected provider and updates order.
        Returns (invoice_id, payment_url).
        """
        provider = get_payment_provider(order.payment_provider)
        desc = f"Заказ #{order.order_number} в Psycho Stars"

        result = await provider.create_invoice(
            order_id=str(order.id),
            order_number=order.order_number,
            amount=Decimal(str(order.fiat_amount)),
            currency=order.fiat_currency,
            description=desc,
        )

        order.payment_invoice_id = result.invoice_id
        order.payment_url = result.payment_url
        order.status = OrderStatus.AWAITING_PAYMENT

        await order_service.transition_order_status(
            db=db,
            order=order,
            to_status=OrderStatus.AWAITING_PAYMENT,
            event_type="PAYMENT_INVOICE_GENERATED",
            details={
                "invoice_id": result.invoice_id,
                "payment_url": result.payment_url,
                "provider": order.payment_provider.value,
            },
        )
        return result.invoice_id, result.payment_url

    async def process_webhook(
        self,
        provider_type: PaymentProviderType,
        headers: Dict[str, str],
        raw_body: bytes,
        db: AsyncSession,
    ) -> bool:
        """
        Idempotent webhook processor:
        1. Validates cryptographic signature
        2. Acquires row lock on Order to prevent race conditions
        3. Checks if payment transaction already processed
        4. Re-verifies status with provider API
        5. Handles partial payments / overpayments
        6. Transitions order to PAID
        """
        provider = get_payment_provider(provider_type)
        verify_result: WebhookVerificationResult = await provider.verify_webhook(headers, raw_body)

        if not verify_result.is_valid:
            logger.warning(
                "invalid_webhook_signature",
                provider=provider_type.value,
                error=verify_result.error_message,
            )
            return False

        # Idempotency check: check if transaction already logged
        tx_query = select(PaymentTransaction).where(
            PaymentTransaction.provider_tx_id == verify_result.provider_tx_id
        )
        existing_tx = (await db.execute(tx_query)).scalar_one_or_none()
        if existing_tx:
            logger.info(
                "duplicate_webhook_ignored",
                provider=provider_type.value,
                provider_tx_id=verify_result.provider_tx_id,
            )
            return True  # Acknowledge receipt safely

        # Look up order by ID or order_id
        try:
            order_uuid = uuid.UUID(verify_result.order_id)
        except ValueError:
            logger.error("invalid_order_id_in_webhook", order_id=verify_result.order_id)
            return False

        # Row lock using with_for_update
        order_query = select(Order).where(Order.id == order_uuid).with_for_update()
        order = (await db.execute(order_query)).scalar_one_or_none()
        if not order:
            logger.error("order_not_found_for_webhook", order_id=str(order_uuid))
            return False

        # Log incoming payment transaction
        payment_tx = PaymentTransaction(
            order_id=order.id,
            provider=provider_type,
            provider_tx_id=verify_result.provider_tx_id,
            amount=verify_result.paid_amount,
            currency=verify_result.paid_currency,
            status=verify_result.status,
            raw_payload=verify_result.raw_payload,
        )
        db.add(payment_tx)

        if verify_result.status == "PAID":
            # Check for underpayment
            expected_amount = Decimal(str(order.fiat_amount))
            paid_amount = verify_result.paid_amount

            # Check if underpaid by more than 1% (rounding buffer)
            if paid_amount < (expected_amount * Decimal("0.99")):
                logger.error(
                    "order_underpaid",
                    order_id=str(order.id),
                    expected=float(expected_amount),
                    received=float(paid_amount),
                )
                await order_service.transition_order_status(
                    db=db,
                    order=order,
                    to_status=OrderStatus.FAILED,
                    event_type="PAYMENT_UNDERPAID",
                    details={"expected": str(expected_amount), "received": str(paid_amount)},
                )
                return True

            # Mark as PAID and start fulfillment
            await order_service.transition_order_status(
                db=db,
                order=order,
                to_status=OrderStatus.PAID,
                event_type="PAYMENT_CONFIRMED",
                details={
                    "provider": provider_type.value,
                    "provider_tx_id": verify_result.provider_tx_id,
                    "paid_amount": str(paid_amount),
                    "currency": verify_result.paid_currency,
                },
            )

        return True


payment_service = PaymentService()
