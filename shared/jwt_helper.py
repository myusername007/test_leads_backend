import os
from typing import Any

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


def create_token(affiliate_id: int) -> str:
    """JWT токен для affiliate_id."""
    return jwt.encode({"id": affiliate_id}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """ decode токен. Raises HTTPException if invalid """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if "id" not in payload:
            raise ValueError("Missing 'id' field")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_affiliate_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> int:
    """FastAPI dependency - affiliate_id from Bearer token"""
    payload = decode_token(credentials.credentials)
    return int(payload["id"])