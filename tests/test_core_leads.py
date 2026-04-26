import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from shared.jwt_helper import create_token
from shared.models import Lead, Offer


def make_mock_lead(
    lead_id: int = 1,
    offer_id: int = 1,
    affiliate_id: int = 1,
    created_at: datetime = None,
) -> MagicMock:
    lead = MagicMock(spec=Lead)
    lead.id = lead_id
    lead.name = "Тест"
    lead.phone = "+380991234567"
    lead.country = "UA"
    lead.offer_id = offer_id
    lead.affiliate_id = affiliate_id
    lead.created_at = created_at or datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    offer = MagicMock(spec=Offer)
    offer.name = f"Offer {offer_id}"
    lead.offer = offer
    return lead


@pytest.fixture
def token() -> str:
    return create_token(1)


@pytest.fixture
def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db_with_leads():
    db = AsyncMock()
    leads = [
        make_mock_lead(1, offer_id=1, created_at=datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)),
        make_mock_lead(2, offer_id=1, created_at=datetime(2024, 6, 15, 14, 0, tzinfo=timezone.utc)),
        make_mock_lead(3, offer_id=2, created_at=datetime(2024, 6, 16, 9, 0, tzinfo=timezone.utc)),
    ]
    result = MagicMock()
    result.scalars.return_value.all.return_value = leads
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.fixture
def app_with_db(mock_db_with_leads):
    from core.main import app
    from shared.database import get_db

    # Зупиняємо воркер при тестах
    with patch("core.app.worker.run_worker", new_callable=AsyncMock):
        app.dependency_overrides[get_db] = lambda: mock_db_with_leads
        yield app
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_leads_group_by_date(app_with_db, headers):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/leads",
            params={"date_from": "2024-06-15", "date_to": "2024-06-16", "group": "date"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["group"] == "date"
    assert data["total"] == 3
    assert len(data["items"]) == 2  # 2 дні: 15 та 16
    assert data["items"][0]["count"] == 2  # 2 ліди 15-го
    assert data["items"][1]["count"] == 1  # 1 лід 16-го


@pytest.mark.asyncio
async def test_get_leads_group_by_offer(app_with_db, headers):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/leads",
            params={"date_from": "2024-06-15", "date_to": "2024-06-16", "group": "offer"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["group"] == "offer"
    assert data["total"] == 3
    assert len(data["items"]) == 2  # 2 офери
    offer_counts = {item["offer_id"]: item["count"] for item in data["items"]}
    assert offer_counts[1] == 2
    assert offer_counts[2] == 1


@pytest.mark.asyncio
async def test_get_leads_no_token():
    from core.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/leads",
            params={"date_from": "2024-06-15", "date_to": "2024-06-16", "group": "date"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_leads_invalid_group(app_with_db, headers):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/leads",
            params={"date_from": "2024-06-15", "date_to": "2024-06-16", "group": "week"},
            headers=headers,
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_leads_date_to_before_date_from(app_with_db, headers):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/leads",
            params={"date_from": "2024-06-20", "date_to": "2024-06-15", "group": "date"},
            headers=headers,
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_leads_empty_result(headers):
    from core.main import app
    from shared.database import get_db

    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    with patch("core.app.worker.run_worker", new_callable=AsyncMock):
        app.dependency_overrides[get_db] = lambda: db
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/leads",
                params={"date_from": "2024-01-01", "date_to": "2024-01-31", "group": "date"},
                headers=headers,
            )
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []