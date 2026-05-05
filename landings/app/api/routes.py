import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from fastapi import APIRouter, Request, Depends, HTTPException, status
from shared.jwt_helper import get_affiliate_id
from shared.redis_client import get_redis
from landings.app.schemas import LeadIn, LeadResponse

router = APIRouter()

LEADS_STREAM = "leads_stream"


@router.post(
    "/lead",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Лід прийнято"},
        401: {"description": "Невалідний або відсутній Bearer токен"},
    },
)
async def create_lead(
    request: Request,
    payload: LeadIn,
    token_affiliate_id: int = Depends(get_affiliate_id),
) -> LeadResponse:
    redis = get_redis()
    try:
        await redis.xadd(
            LEADS_STREAM,
            {"payload": json.dumps({
                "flow_id": payload.flow_id,
                "name": payload.name,
                "phone": payload.phone,
                "country": payload.country,
                "ip": request.client.host if request.client else "",
            })}
        )
    finally:
        await redis.aclose()

    return LeadResponse()