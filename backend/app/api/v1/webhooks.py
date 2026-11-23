from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.database import get_db
from app.models.order import PaymentProviderType
from app.payments.service import payment_service

router = APIRouter(prefix="/webhooks", tags=["Payment Webhooks"])


@router.post("/cryptobot")
async def cryptobot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook handler for CryptoBot payments.
    Verifies crypto-pay-api-signature header on raw payload bytes.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    success = await payment_service.process_webhook(
        provider_type=PaymentProviderType.CRYPTOBOT,
        headers=headers,
        raw_body=raw_body,
        db=db,
    )

    if not success:
        logger.warning("cryptobot_webhook_rejected")
        # Return 200 to prevent continuous webhook hammering from provider if signature was invalid
        return {"ok": False, "detail": "Invalid signature or payload"}

    return {"ok": True}


@router.post("/lavapay")
async def lavapay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook handler for Lava Pay payments.
    Verifies Signature header on raw payload bytes.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    success = await payment_service.process_webhook(
        provider_type=PaymentProviderType.LAVAPAY,
        headers=headers,
        raw_body=raw_body,
        db=db,
    )

    if not success:
        logger.warning("lavapay_webhook_rejected")
        return {"ok": False, "detail": "Invalid signature or payload"}

    return {"ok": True}
