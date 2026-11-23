from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AuthInitDataRequest(BaseModel):
    init_data: str = Field(..., description="Raw initData string provided by Telegram WebApp SDK")


class TelegramUserAuth(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = False
    allows_write_to_pm: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_premium: bool = False
    is_blocked: bool = False
    is_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
