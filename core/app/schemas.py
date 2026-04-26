from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class LeadItem(BaseModel):

    id: int
    name: str
    phone: str
    country: str
    offer_id: int
    affiliate_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupByDateItem(BaseModel):

    date: date
    count: int
    leads: list[LeadItem]


class GroupByOfferItem(BaseModel):

    offer_id: int
    offer_name: str
    count: int
    leads: list[LeadItem]


class LeadsResponse(BaseModel):

    date_from: date
    date_to: date
    group: Literal["date", "offer"]
    total: int
    items: list[GroupByDateItem] | list[GroupByOfferItem]


class LeadsQueryParams(BaseModel):

    date_from: date
    date_to: date
    group: Literal["date", "offer"]

    @field_validator("date_to")
    @classmethod
    def date_to_gte_date_from(cls, v: date, info) -> date:
        date_from = info.data.get("date_from")
        if date_from and v < date_from:
            raise ValueError("date_to має бути >= date_from")
        return v