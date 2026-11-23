import os
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.config import Settings, get_settings
from app.main import app


def test_settings_load():
    settings = Settings(
        APP_NAME="Psycho Stars Test",
        ADMIN_IDS="111,222,333",
        ENVIRONMENT="test",
    )
    assert settings.APP_NAME == "Psycho Stars Test"
    assert settings.admin_ids == [111, 222, 333]
    assert settings.ENVIRONMENT == "test"


@pytest.mark.asyncio
async def test_healthcheck_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "environment" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "/health" in data["health"]


def test_deployment_artifacts_exist():
    root = Path(__file__).resolve().parent.parent
    assert (root / "docker-compose.yml").is_file()
    assert (root / ".env.example").is_file()
    assert (root / "caddy" / "Caddyfile").is_file()
    assert (root / "backend" / "Dockerfile").is_file()
    assert (root / "bot" / "Dockerfile").is_file()
    assert (root / "frontend" / "Dockerfile").is_file()
