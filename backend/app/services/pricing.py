from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple
from app.config import get_settings
from app.core.logger import logger

settings = get_settings()

# Default fallback rates if API/DB is down during cold start
DEFAULT_TON_RATES = {
    "TON_RUB": Decimal("520.00"),
    "TON_USDT": Decimal("5.50"),
}


class CircuitBreakerException(Exception):
    """Raised when currency volatility exceeds security safety limit"""
    pass


class PricingService:
    def __init__(self):
        self._rates_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._last_reference_rates: Dict[str, Decimal] = {}

    def get_ton_rate(self, target_currency: str = "RUB", override_rate: Optional[Decimal] = None) -> Decimal:
        pair = f"TON_{target_currency.upper()}"
        if override_rate is not None:
            return override_rate
        return DEFAULT_TON_RATES.get(pair, Decimal("500.00"))

    def check_volatility(
        self,
        current_rate: Decimal,
        reference_rate: Decimal,
        max_allowed_percent: Optional[float] = None,
    ) -> bool:
        """
        Circuit breaker to prevent selling during flash crashes or price manipulation.
        Returns True if safe, False if volatility threshold is breached.
        """
        threshold = max_allowed_percent or settings.CIRCUIT_BREAKER_PRICE_CHANGE_PERCENT
        if reference_rate <= 0:
            return True

        diff_percent = abs((current_rate - reference_rate) / reference_rate) * Decimal("100.0")
        if diff_percent > Decimal(str(threshold)):
            logger.critical(
                "circuit_breaker_triggered",
                current_rate=float(current_rate),
                reference_rate=float(reference_rate),
                diff_percent=float(diff_percent),
                threshold=threshold,
            )
            return False
        return True

    def calculate_price(
        self,
        base_price_ton: Decimal,
        quantity: int,
        margin_percent: Decimal,
        target_currency: str = "RUB",
        override_rate: Optional[Decimal] = None,
        reference_rate: Optional[Decimal] = None,
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculates:
        1. Applied TON rate
        2. Final price in target currency (Decimal with 2 decimal places)

        Formula:
        Raw = BasePriceTON * Quantity * TON_Rate
        Final = Raw * (1 + Margin / 100)
        """
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        current_rate = self.get_ton_rate(target_currency, override_rate=override_rate)

        # Check circuit breaker if reference rate provided
        if reference_rate:
            if not self.check_volatility(current_rate, reference_rate):
                raise CircuitBreakerException(
                    "Trading is temporarily halted due to extreme TON exchange rate volatility."
                )

        raw_ton_total = base_price_ton * Decimal(str(quantity))
        raw_fiat = raw_ton_total * current_rate

        multiplier = Decimal("1.0") + (margin_percent / Decimal("100.0"))
        final_price = (raw_fiat * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return current_rate, final_price


pricing_service = PricingService()
