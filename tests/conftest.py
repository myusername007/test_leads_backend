import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from shared.jwt_helper import create_token


@pytest.fixture
def affiliate_id() -> int:
    return 1


@pytest.fixture
def token(affiliate_id: int) -> str:
    return create_token(affiliate_id)


@pytest.fixture
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}