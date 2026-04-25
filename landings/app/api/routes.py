import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.jwt_helper import get_affiliate_id
from shared.models import Affiliate, Offer
from shared.redis_client import LEADS_QUEUE, get_redis
from landings.app.schemas import LeadIn, LeadResponse

router = APIRouter()


@router.post(
    "/lead",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Лід прийнято"},
        400: {"description": "affiliate_id не збігається з токеном"},
        401: {"description": "Невалідний або відсутній Bearer токен"},
        404: {"description": "Offer або Affiliate не знайдено"},
    },
)
async def create_lead(
    payload: LeadIn,
    token_affiliate_id: int = Depends(get_affiliate_id),
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    # affiliate_id у тілі має збігатися з токеном
    if payload.affiliate_id != token_affiliate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="affiliate_id у запиті не збігається з токеном",
        )

    # Affiliate існує в БД
    affiliate = await db.get(Affiliate, payload.affiliate_id)
    if affiliate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affiliate {payload.affiliate_id} не знайдено",
        )

    # Offer існує в БД
    offer = await db.get(Offer, payload.offer_id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {payload.offer_id} не знайдено",
        )

    # Redis
    redis = get_redis()
    try:
        await redis.lpush(LEADS_QUEUE, json.dumps(payload.model_dump()))
    finally:
        await redis.aclose()

    return LeadResponse()