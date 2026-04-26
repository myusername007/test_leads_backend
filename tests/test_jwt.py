import pytest
import jwt

from shared.jwt_helper import JWT_SECRET, JWT_ALGORITHM, create_token, decode_token
from fastapi import HTTPException


def test_create_and_decode_token():
    token = create_token(42)
    payload = decode_token(token)
    assert payload["id"] == 42


def test_decode_invalid_token():
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.valid.token")
    assert exc.value.status_code == 401


def test_decode_token_missing_id():
    # Токен без поля id
    bad_token = jwt.encode({"sub": "test"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        decode_token(bad_token)
    assert exc.value.status_code == 401


def test_create_token_returns_string():
    token = create_token(1)
    assert isinstance(token, str)
    assert len(token) > 0


def test_different_affiliates_different_tokens():
    t1 = create_token(1)
    t2 = create_token(2)
    assert t1 != t2