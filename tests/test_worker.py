import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


LEAD_DATA = {
    "name": "Тест",
    "phone": "+380991234567",
    "country": "UA",
    "offer_id": 1,
    "affiliate_id": 1,
}


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.brpop = AsyncMock()
    redis.set = AsyncMock()
    redis.aclose = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_process_lead_new(mock_redis):
    mock_redis.set = AsyncMock(return_value=True)  # NX успішно

    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # add() SQLAlchemy
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("core.app.worker.AsyncSessionFactory", return_value=mock_session):
        from core.app.worker import process_lead
        await process_lead(LEAD_DATA, mock_redis)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_lead_duplicate(mock_redis):
    """Дублікат — не записується в БД."""
    mock_redis.set = AsyncMock(return_value=None)  #дублікат

    mock_session = AsyncMock()

    with patch("core.app.worker.AsyncSessionFactory", return_value=mock_session):
        from core.app.worker import process_lead
        await process_lead(LEAD_DATA, mock_redis)

    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_dedup_key_format():
    from core.app.worker import _dedup_key
    key = _dedup_key(LEAD_DATA)
    assert key == "dedup:Тест:+380991234567:1:1"


@pytest.mark.asyncio
async def test_dedup_key_uniqueness():
    from core.app.worker import _dedup_key
    lead2 = {**LEAD_DATA, "phone": "+380000000000"}
    assert _dedup_key(LEAD_DATA) != _dedup_key(lead2)


@pytest.mark.asyncio
async def test_process_lead_redis_ttl(mock_redis):
    mock_redis.set = AsyncMock(return_value=True)
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("core.app.worker.AsyncSessionFactory", return_value=mock_session):
        from core.app.worker import process_lead
        from shared.redis_client import DEDUP_TTL
        await process_lead(LEAD_DATA, mock_redis)

    mock_redis.set.assert_called_once()
    call_kwargs = mock_redis.set.call_args
    assert call_kwargs.kwargs.get("ex") == DEDUP_TTL
    assert call_kwargs.kwargs.get("nx") is True