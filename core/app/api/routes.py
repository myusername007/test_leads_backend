from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database import get_db
from shared.jwt_helper import get_affiliate_id
from shared.models import Lead, Offer
from core.app.schemas import (
    GroupByDateItem,
    GroupByOfferItem,
    LeadItem,
    LeadsResponse,
)

router = APIRouter()


def _to_utc_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


def _to_utc_end(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)


@router.get(
    "/leads",
    response_model=LeadsResponse,
    responses={
        200: {"description": "Успішна відповідь"},
        401: {"description": "Невалідний або відсутній Bearer токен"},
        422: {"description": "Невалідні query параметри"},
    },
)
async def get_leads(
    date_from: date = Query(..., description="Початок періоду (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Кінець періоду (YYYY-MM-DD)"),
    group: str = Query(..., description="Групування: date або offer"),
    affiliate_id: int = Depends(get_affiliate_id),
    db: AsyncSession = Depends(get_db),
) -> LeadsResponse:
    if group not in ("date", "offer"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="group має бути 'date' або 'offer'")

    if date_to < date_from:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="date_to має бути >= date_from")

    # Запит з eager load offer для групування по offer_name
    stmt = (
        select(Lead)
        .where(
            and_(
                Lead.affiliate_id == affiliate_id,
                Lead.created_at >= _to_utc_start(date_from),
                Lead.created_at <= _to_utc_end(date_to),
            )
        )
        .options(selectinload(Lead.offer))
        .order_by(Lead.created_at)
    )
    result = await db.execute(stmt)
    leads = result.scalars().all()

    lead_items = [LeadItem.model_validate(l) for l in leads]

    if group == "date":
        grouped: dict[date, list[LeadItem]] = defaultdict(list)
        for item in lead_items:
            grouped[item.created_at.date()].append(item)

        items = [
            GroupByDateItem(date=d, count=len(lst), leads=lst)
            for d, lst in sorted(grouped.items())
        ]
    else:  # offer
        grouped_offer: dict[int, dict] = {}
        for lead, item in zip(leads, lead_items):
            oid = item.offer_id
            if oid not in grouped_offer:
                grouped_offer[oid] = {
                    "offer_id": oid,
                    "offer_name": lead.offer.name if lead.offer else str(oid),
                    "leads": [],
                }
            grouped_offer[oid]["leads"].append(item)

        items = [
            GroupByOfferItem(
                offer_id=v["offer_id"],
                offer_name=v["offer_name"],
                count=len(v["leads"]),
                leads=v["leads"],
            )
            for v in grouped_offer.values()
        ]

    return LeadsResponse(
        date_from=date_from,
        date_to=date_to,
        group=group,
        total=len(lead_items),
        items=items,
    )