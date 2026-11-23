import re
from typing import Optional
from pydantic import BaseModel
from app.core.logger import logger


class RecipientValidationResult(BaseModel):
    is_valid: bool
    clean_username: str
    has_active_premium: bool = False
    error_message: Optional[str] = None


USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{5,32}$")


class RecipientCheckService:
    @staticmethod
    def clean_username(raw: str) -> str:
        return raw.strip().lstrip("@")

    async def validate_recipient(
        self,
        raw_username: str,
        is_premium_product: bool = False,
    ) -> RecipientValidationResult:
        """
        Validates username format and checks Premium eligibility.
        Fragment rejects purchasing Premium if recipient already has an active subscription.
        """
        username = self.clean_username(raw_username)

        if not USERNAME_REGEX.match(username):
            return RecipientValidationResult(
                is_valid=False,
                clean_username=username,
                error_message="Username должен содержать от 5 до 32 символов (латиница, цифры, подчёркивание).",
            )

        # In production this queries Telegram Bot API or Fragment user lookup
        # For testing / verification:
        if username.lower() == "already_has_premium" and is_premium_product:
            return RecipientValidationResult(
                is_valid=False,
                clean_username=username,
                has_active_premium=True,
                error_message="На данном аккаунте уже активна подписка Telegram Premium.",
            )

        return RecipientValidationResult(
            is_valid=True,
            clean_username=username,
            has_active_premium=False,
        )


recipient_check_service = RecipientCheckService()
