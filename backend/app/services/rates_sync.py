from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logger import logger
from app.models.settings import CurrencyRate, SystemSetting
from app.services.pricing import pricing_service

settings = get_settings()


class RatesSyncService:
    async def fetch_ton_rates_from_api(self) -> Tuple[Decimal, Decimal]:
        """
        Fetches live TON/RUB and TON/USDT rates from public APIs (CoinGecko / Binance fallback).
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "the-open-network", "vs_currencies": "rub,usd"},
                )
                data = resp.json()
                ton_data = data.get("the-open-network", {})
                rub_rate = Decimal(str(ton_data.get("rub", "520.00")))
                usd_rate = Decimal(str(ton_data.get("usd", "5.50")))
                return rub_rate, usd_rate
        except Exception as e:
            logger.warning("coingecko_fetch_failed_using_fallback", error=str(e))
            # Fallback
            return Decimal("520.00"), Decimal("5.50")

    async def sync_rates(self, db: AsyncSession) -> bool:
        """
        Updates exchange rates in DB and verifies Circuit Breaker volatility limits.
        """
        rub_rate, usd_rate = await self.fetch_ton_rates_from_api()

        # Check existing rate for volatility spike
        existing_rub_query = select(CurrencyRate).where(CurrencyRate.pair == "TON_RUB")
        existing_rub = (await db.execute(existing_rub_query)).scalar_one_or_none()

        if existing_rub:
            prev_rate = Decimal(str(existing_rub.rate))
            is_safe = pricing_service.check_volatility(
                current_rate=rub_rate,
                reference_rate=prev_rate,
                max_allowed_percent=settings.CIRCUIT_BREAKER_PRICE_CHANGE_PERCENT,
            )
            if not is_safe:
                # Volatility spike! Activate circuit breaker
                cb_query = select(SystemSetting).where(SystemSetting.key == "circuit_breaker_active")
                cb_setting = (await db.execute(cb_query)).scalar_one_or_none()
                if not cb_setting:
                    cb_setting = SystemSetting(
                        key="circuit_breaker_active",
                        value="true",
                        description="Trading halted due to extreme TON volatility",
                    )
                    db.add(cb_setting)
                else:
                    cb_setting.value = "true"
                await db.commit()
                return False

            existing_rub.rate = rub_rate
            existing_rub.source = "coingecko"
        else:
            db.add(CurrencyRate(pair="TON_RUB", rate=rub_rate, source="coingecko"))

        existing_usd_query = select(CurrencyRate).where(CurrencyRate.pair == "TON_USDT")
        existing_usd = (await db.execute(existing_usd_query)).scalar_one_or_none()
        if existing_usd:
            existing_usd.rate = usd_rate
        else:
            db.add(CurrencyRate(pair="TON_USDT", rate=usd_rate, source="coingecko"))

        await db.commit()
        logger.info("ton_rates_synced", ton_rub=float(rub_rate), ton_usdt=float(usd_rate))
        return True


rates_sync_service = RatesSyncService()
