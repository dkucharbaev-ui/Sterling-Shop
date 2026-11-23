import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, validate_telegram_init_data
from app.database import Base, get_db
from app.main import app

TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"


def generate_valid_init_data(user_dict: dict, bot_token: str, auth_date: int = None) -> str:
    """Helper to produce cryptographically valid Telegram initData"""
    if auth_date is None:
        auth_date = int(time.time())

    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrP-G",
        "user": json.dumps(user_dict, separators=(",", ":")),
    }

    # Sort keys
    sorted_items = sorted(params.items(), key=lambda x: x[0])
    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_items])

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    params["hash"] = calc_hash
    return urlencode(params)


def test_hmac_valid_init_data():
    user = {"id": 12345678, "first_name": "Pavel", "username": "durov"}
    init_data = generate_valid_init_data(user, TEST_BOT_TOKEN)

    auth_user = validate_telegram_init_data(init_data, TEST_BOT_TOKEN)
    assert auth_user.id == 12345678
    assert auth_user.first_name == "Pavel"
    assert auth_user.username == "durov"


def test_hmac_tampered_data():
    user = {"id": 12345678, "first_name": "Pavel", "username": "durov"}
    init_data = generate_valid_init_data(user, TEST_BOT_TOKEN)

    # Malicious actor changes user id from 12345678 to 99999999 in URL
    tampered_data = init_data.replace("12345678", "99999999")

    with pytest.raises(ValueError, match="Invalid init_data signature"):
        validate_telegram_init_data(tampered_data, TEST_BOT_TOKEN)


def test_hmac_expired_auth_date():
    user = {"id": 12345678, "first_name": "Pavel"}
    # 2 days old
    old_date = int(time.time()) - (86400 * 2)
    init_data = generate_valid_init_data(user, TEST_BOT_TOKEN, auth_date=old_date)

    with pytest.raises(ValueError, match="init_data has expired"):
        validate_telegram_init_data(init_data, TEST_BOT_TOKEN, max_age_seconds=86400)


def test_hmac_missing_hash():
    with pytest.raises(ValueError, match="hash parameter is missing"):
        validate_telegram_init_data("auth_date=1700000000&user=%7B%7D", TEST_BOT_TOKEN)


def test_jwt_lifecycle():
    token = create_access_token(subject=777888)
    payload = decode_access_token(token)
    assert payload["sub"] == "777888"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_auth_telegram_api_endpoint():
    # Setup in-memory sqlite db for this test
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    settings = get_settings()
    settings.BOT_TOKEN = TEST_BOT_TOKEN

    user_info = {"id": 98765432, "first_name": "Danis", "username": "danis_k"}
    valid_data = generate_valid_init_data(user_info, TEST_BOT_TOKEN)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test auth endpoint
        response = await client.post("/api/v1/auth/telegram", json={"init_data": valid_data})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["id"] == 98765432
        assert data["user"]["username"] == "danis_k"

        token = data["access_token"]

        # Test /api/v1/auth/me with valid Bearer token
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["id"] == 98765432
        assert me_data["first_name"] == "Danis"

        # Test /api/v1/auth/me with missing/invalid token
        unauth_response = await client.get("/api/v1/auth/me")
        assert unauth_response.status_code == 401

    app.dependency_overrides.clear()
