from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    APP_NAME: str = "Psycho Stars"
    APP_DOMAIN: str = "localhost"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "development-insecure-secret-key-must-be-changed-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Telegram Bot
    BOT_TOKEN: str = "1234567890:TEST_BOT_TOKEN_DEVELOPMENT"
    BOT_USERNAME: str = "PsychoStarsBot"
    MINI_APP_URL: str = "https://localhost"
    ADMIN_IDS_RAW: str = Field(default="", alias="ADMIN_IDS")

    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_IDS_RAW:
            return []
        ids = []
        for x in self.ADMIN_IDS_RAW.split(","):
            x = x.strip()
            if x.isdigit():
                ids.append(int(x))
        return ids

    # Database & Redis
    DATABASE_URL: str = "postgresql+asyncpg://psychouser:psychopassword@localhost:5432/psychostars"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Payment Gateways
    CRYPTOBOT_API_TOKEN: str = ""
    CRYPTOBOT_NETWORK: str = "testnet"  # mainnet | testnet
    LAVAPAY_SHOP_ID: str = ""
    LAVAPAY_SECRET_KEY: str = ""
    LAVAPAY_ADDITIONAL_KEY: str = ""

    # TON & Fragment Fulfillment
    TON_NETWORK: str = "testnet"  # mainnet | testnet
    TON_WALLET_MNEMONIC: str = ""
    TON_WALLET_VERSION: str = "v4r2"
    MIN_TON_BALANCE_ALERT: float = 5.0
    CRITICAL_TON_BALANCE_PAUSE: float = 1.0
    DRY_RUN_FULFILLMENT: bool = True
    RESELLER_API_URL: Optional[str] = None
    RESELLER_API_KEY: Optional[str] = None

    # Pricing & Volatility Shield
    DEFAULT_MARGIN_PERCENT: float = 15.0
    CIRCUIT_BREAKER_PRICE_CHANGE_PERCENT: float = 10.0
    RATES_CACHE_TTL_SECONDS: int = 300

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["*"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
