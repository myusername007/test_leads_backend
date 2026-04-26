import json
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from shared.jwt_helper import create_token
from shared.models import Affiliate, Offer


def make_lead(affiliate_id: int = 1, offer_id: int = 1) -> dict:
    return {
        "name": "Тест",
        "phone": "+380991234567",
        "country": "UA",
        "offer_id": offer_id,
        "affiliate_id": affiliate_id,
    }


@pytest.fixture
def token() -> str:
    return create_token(1)


@pytest.fixture
def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # db.get повертає об'єкти за замовчуванням
    db.get = AsyncMock(side_effect=lambda model, pk: MagicMock(id=pk, name="Test"))
    return db


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.lpush = AsyncMock(return_value=1)
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def app_client(mock_db, mock_redis):
    from landings.main import app
    from shared.database import get_db
    from shared.redis_client import get_redis

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("landings.app.api.routes.get_redis", return_value=mock_redis):
        yield app

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_lead_success(app_client, headers):
    async with AsyncClient(
        transport=ASGITransport(app=app_client), base_url="http://test"
    ) as client:
        resp = await client.post("/lead", json=make_lead(), headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_create_lead_no_token():
    from landings.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/lead", json=make_lead())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_lead_wrong_affiliate_id(app_client, headers):
    """affiliate_id у тілі відрізняється від токена (токен = 1, тіло = 2)."""
    async with AsyncClient(
        transport=ASGITransport(app=app_client), base_url="http://test"
    ) as client:
        resp = await client.post("/lead", json=make_lead(affiliate_id=2), headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_lead_invalid_country(app_client, headers):
    payload = make_lead()
    payload["country"] = "XX"
    async with AsyncClient(
        transport=ASGITransport(app=app_client), base_url="http://test"
    ) as client:
        resp = await client.post("/lead", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_invalid_phone(app_client, headers):
    payload = make_lead()
    payload["phone"] = "not-a-phone"
    async with AsyncClient(
        transport=ASGITransport(app=app_client), base_url="http://test"
    ) as client:
        resp = await client.post("/lead", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_affiliate_not_found(headers, mock_redis):
    from landings.main import app
    from shared.database import get_db

    db = AsyncMock()
    # Affiliate не знайдено
    db.get = AsyncMock(return_value=None)

    app.dependency_overrides[get_db] = lambda: db
    with patch("landings.app.api.routes.get_redis", return_value=mock_redis):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/lead", json=make_lead(), headers=headers)

    app.dependency_overrides.clear()
    assert resp.status_code == 404