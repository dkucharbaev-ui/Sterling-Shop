import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, unquote

import jwt
from app.config import get_settings
from app.schemas.auth import TelegramUserAuth

settings = get_settings()

ALGORITHM = "HS256"


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> TelegramUserAuth:
    """
    Validates Telegram WebApp initData string against Bot Token using HMAC-SHA256.
    Follows Telegram Official Mini Apps Specification.
    """
    if not init_data:
        raise ValueError("init_data is empty")

    parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise ValueError("hash parameter is missing from init_data")

    # Check auth_date for freshness
    auth_date_raw = parsed_data.get("auth_date")
    if not auth_date_raw:
        raise ValueError("auth_date parameter is missing from init_data")

    try:
        auth_date = int(auth_date_raw)
    except ValueError:
        raise ValueError("Invalid auth_date format")

    current_timestamp = int(time.time())
    if current_timestamp - auth_date > max_age_seconds:
        raise ValueError("init_data has expired (auth_date too old)")

    # Construct data_check_string: key=value sorted alphabetically separated by newline
    sorted_items = sorted(parsed_data.items(), key=lambda item: item[0])
    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_items])

    # secret_key = HMAC_SHA256(b"WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # calculated_hash = HMAC_SHA256(secret_key, data_check_string)
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Constant time comparison to prevent timing attacks
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Invalid init_data signature (HMAC verification failed)")

    user_raw = parsed_data.get("user")
    if not user_raw:
        raise ValueError("user parameter is missing from init_data")

    try:
        user_dict = json.loads(user_raw)
        return TelegramUserAuth(**user_dict)
    except Exception as e:
        raise ValueError(f"Failed to parse user data: {e}")


def create_access_token(
    subject: str | int,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generates a short-lived signed JWT for authorized user sessions.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")
